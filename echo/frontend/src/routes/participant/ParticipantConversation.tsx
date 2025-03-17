import WelcomeImage from "@/assets/participant-welcome-pattern.png";
import { Markdown } from "@/components/common/Markdown";
import { useI18nNavigate } from "@/hooks/useI18nNavigate";
import { I18nLink } from "@/components/common/i18nLink";
import {
  useUploadConversationChunk,
  useUploadConversationTextChunk,
} from "@/lib/query";
import {
  ActionIcon,
  Box,
  Button,
  Divider,
  Group,
  Loader,
  LoadingOverlay,
  Menu,
  Modal,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconCheck,
  IconDotsVertical,
  IconMicrophone,
  IconPlayerPause,
  IconPlayerPlay,
  IconPlayerStop,
  IconQuestionMark,
  IconReload,
  IconTextCaption,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import {
  PropsWithChildren,
  ReactHTMLElement,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useParams } from "react-router-dom";

import { useLanguage } from "@/hooks/useLanguage";
import { useWakeLock } from "@/hooks/useWakeLock";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import clsx from "clsx";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  deleteParticipantConversationChunk,
  finishConversation,
  getParticipantConversationChunks,
} from "@/lib/api";
import { useParticipantProjectById } from "@/lib/participantQuery";
import { useDisclosure } from "@mantine/hooks";
import { t } from "@lingui/core/macro";
import { Trans } from "@lingui/react/macro";
import { directus } from "@/lib/directus";
import { readItem, readItems } from "@directus/sdk";
import { Logo } from "@/components/common/Logo";

const preferredMimeTypes = ["audio/webm", "audio/wav", "video/mp4"];

const getSupportedMimeType = () => {
  for (const mimeType of preferredMimeTypes) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }
  return "audio/webm";
};

const defaultMimeType = getSupportedMimeType();

const checkPermissionError = async () => {
  try {
    // @ts-expect-error microphone is not available?
    const result = await navigator.permissions.query({ name: "microphone" });
    if (result.state === "denied") {
      return "denied" as const;
    } else if (result.state === "prompt") {
      return "prompt" as const;
    } else if (result.state === "granted") {
      return "granted" as const;
    } else {
      return "error" as const;
    }
  } catch (error) {
    console.error("Error checking microphone permissions", error);
    return "error" as const;
  }
};

interface UseAudioRecorderOptions {
  onChunk: (chunk: Blob) => void;
  mimeType?: string;
  timeslice?: number;
  debug?: boolean;
}

interface UseAudioRecorderResult {
  startRecording: () => void;
  stopRecording: () => void;
  pauseRecording: () => void;
  resumeRecording: () => void;
  isRecording: boolean;
  isPaused: boolean;
  recordingTime: number;
  errored:
    | boolean
    | {
        message: string;
      };
  loading: boolean;
  permissionError: string | null;
}

const useChunkedAudioRecorder = ({
  onChunk,
  mimeType = defaultMimeType,
  timeslice = 30000, // 30 sec
  // timeslice = 300000, // 5 min
  debug = false,
}: UseAudioRecorderOptions): UseAudioRecorderResult => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [userPaused, setUserPaused] = useState(false);

  const isRecordingRef = useRef(isRecording);
  const isPausedRef = useRef(isPaused);
  const userPausedRef = useRef(userPaused);

  const [recordingTime, setRecordingTime] = useState(0);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startRecordingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<AudioWorkletNode | null>(null);

  const [permissionError, setPermissionError] = useState<string | null>(null);

  const log = (...args: any[]) => {
    if (debug) {
      console.log(...args);
    }
  };

  useEffect(() => {
    // for syncing
    isRecordingRef.current = isRecording;
    isPausedRef.current = isPaused;
    userPausedRef.current = userPaused;
  }, [isRecording, isPaused, userPaused]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const updateRecordingTime = useCallback(() => {
    setRecordingTime((prev) => prev + 1);
  }, []);

  const chunkBufferRef = useRef<Blob[]>([]);

  const startRecordingChunk = useCallback(() => {
    log("startRecordingChunk", {
      isRecording,
      mediaRecorderRefState: mediaRecorderRef.current?.state,
    });
    if (!streamRef.current) {
      log("startRecordingChunk: no stream found");
      return;
    }

    // Ensure that any previous MediaRecorder instance is stopped before creating a new one
    if (mediaRecorderRef.current) {
      log("startRecordingChunk: stopping previous MediaRecorder instance");
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }

    log("startRecordingChunk: creating new MediaRecorder instance");
    const recorder = new MediaRecorder(streamRef.current, {
      mimeType: MediaRecorder.isTypeSupported(mimeType)
        ? mimeType
        : "audio/webm",
    });
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      log("ondataavailable", event.data.size, "bytes");
      if (event.data.size > 0) {
        chunkBufferRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      log("MediaRecorder stopped");
      onChunk(new Blob(chunkBufferRef.current, { type: mimeType }));

      startRecordingChunk();

      // flush the buffer
      chunkBufferRef.current = [];
    };

    // allow for some room to restart so all is just one chunk as per mediarec
    recorder.start(timeslice * 2);
  }, [isRecording]);

  const startRecording = async () => {
    try {
      log("Requesting access to the microphone...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      log("Access to microphone granted.", { stream });

      log("Creating MediaRecorder instance");

      setIsRecording(true);
      setIsPaused(false);
      setUserPaused(false);
      startRecordingChunk();

      // allow to restart recording chunk
      startRecordingIntervalRef.current = setInterval(() => {
        log("Checking if MediaRecorder should be stopped");
        if (mediaRecorderRef.current?.state === "recording") {
          log("attempting to Stop recording chunk");
          mediaRecorderRef.current.stop();

          log("attempt to Restart recording chunk", {
            isRecording,
            mediaRecorderRefState: mediaRecorderRef.current?.state,
          });

          if (isRecording) {
            log("Restarting recording chunk");
            startRecordingChunk();
          }
        }
      }, timeslice);

      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      intervalRef.current = setInterval(updateRecordingTime, 1000);
    } catch (error) {
      console.error("Error accessing audio stream", error);
      setPermissionError("Error accessing audio stream");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setIsPaused(false);
    setUserPaused(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    setRecordingTime(0);
    if (startRecordingIntervalRef.current)
      clearInterval(startRecordingIntervalRef.current);
    // remove the worker
    audioProcessorRef.current?.disconnect();
    audioProcessorRef.current = null;
    // close the audio context
    audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const pauseRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }
  };

  const userPauseRecording = () => {
    pauseRecording();
    setUserPaused(true);
  };

  const resumeRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "paused"
    ) {
      mediaRecorderRef.current.resume();
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      intervalRef.current = setInterval(updateRecordingTime, 1000);
      setIsPaused(false);
      setUserPaused(false);
    }
  };

  const userResumeRecording = () => {
    resumeRecording();
    setUserPaused(false);
  };

  return {
    startRecording,
    stopRecording,
    pauseRecording: userPauseRecording,
    resumeRecording: userResumeRecording,
    isRecording,
    isPaused,
    recordingTime,
    loading: false,
    errored: false,
    permissionError,
  };
};

const useConversationQuery = (
  projectId: string | undefined,
  conversationId: string | undefined,
) => {
  return useQuery({
    queryKey: ["participant", "conversation", projectId, conversationId],
    queryFn: () =>
      directus.request(readItem("conversation", conversationId ?? "")),
    enabled: !!conversationId,
    refetchInterval: 30000,
  });
};

const useConversationChunksQuery = (
  projectId: string | undefined,
  conversationId: string | undefined,
) => {
  return useQuery({
    queryKey: ["participant", "conversation_chunks", conversationId],
    queryFn: () =>
      getParticipantConversationChunks(projectId ?? "", conversationId ?? ""),
    enabled: !!conversationId,
    refetchInterval: 15000,
  });
};

const useConversationRepliesQuery = (conversationId: string | undefined) => {
  return useQuery({
    queryKey: ["participant", "conversation_replies", conversationId],
    queryFn: () =>
      directus.request(
        readItems("conversation_reply", {
          filter: { conversation_id: { _eq: conversationId } },
          fields: ["id", "content_text", "date_created", "type"],
        }),
      ),
    enabled: !!conversationId,
    refetchInterval: 15000,
  });
};

const useConversationReplyMutation = () => {
  const queryClient = useQueryClient();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  
  const mutation = useMutation({
    mutationFn: async ({
      conversationId,
      language,
    }: {
      conversationId: string;
      language: string;
    }): Promise<void> => {
      setIsStreaming(true);
      setStreamingContent("");
      
      try {
        const response = await fetch(
          `/api/conversations/${conversationId}/get-reply`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language }),
          }
        );

        if (!response.ok || !response.body) {
          throw new Error('Network response was not ok');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(5));
              setStreamingContent(prev => prev + data.content);
            }
          }
        }

        // Wait longer before invalidating to ensure Directus has saved
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Invalidate and wait for refetch
        await queryClient.invalidateQueries({
          queryKey: ["participant", "conversation_replies", conversationId],
        });

        // Don't clear streaming content - let it persist until page refresh
      } finally {
        setIsStreaming(false);
        // setStreamingContent("");
      }
    },
  });

  return {
    ...mutation,
    isStreaming,
    streamingContent,
    mutateAsync: mutation.mutateAsync,
  };
};

type ConversationReplyMutation = ReturnType<typeof useConversationReplyMutation>;

const UserChunkMessage = ({
  chunk,
  hide,
}: {
  chunk?: TConversationChunk;
  hide?: boolean;
}) => {
  const { projectId, conversationId } = useParams();
  const queryClient = useQueryClient();

  const deleteChunkMutation = useMutation({
    mutationFn: ({
      projectId,
      conversationId,
      chunkId,
    }: {
      projectId: string;
      conversationId: string;
      chunkId: string;
    }) =>
      deleteParticipantConversationChunk(
        projectId ?? "",
        conversationId ?? "",
        chunkId ?? "",
      ),
    onMutate: (vars) => {
      queryClient.cancelQueries({
        queryKey: ["participant", "conversation_chunks", conversationId ?? ""],
      });
      const previousValue = queryClient.getQueryData([
        "participant",
        "conversation_chunks",
        conversationId ?? "",
      ]);
      queryClient.setQueryData(
        ["participant", "conversation_chunks", conversationId ?? ""],

        (old: TConversationChunk[] | undefined) =>
          old?.filter((c) => c.id !== vars.chunkId),
      );
      return previousValue;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["participant", "conversation_chunks", conversationId ?? ""],
      });
    },
  });

  if (!chunk) return <></>;
  if (hide) return <></>;

  const handleDelete = () => {
    deleteChunkMutation.mutate({
      projectId: projectId ?? "",
      conversationId: conversationId ?? "",
      chunkId: chunk.id,
    });
  };

  return (
    <div className="align-center flex justify-end">
      <div>
        <Menu shadow="md" width={200}>
          <Menu.Target>
            <ActionIcon variant="transparent" c="gray" className="h-full">
              <IconDotsVertical />
            </ActionIcon>
          </Menu.Target>

          <Menu.Dropdown>
            <Menu.Item
              onClick={handleDelete}
              disabled={deleteChunkMutation.isPending}
              leftSection={<IconTrash />}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </div>
      <Paper className="rounded-t-xl rounded-bl-xl p-4 shadow-sm">
        <Text className="prose text-sm">
          {chunk.transcript == null && (
            <Markdown content={t`*Transcription in progress.*`} />
          )}
          <Markdown content={chunk.transcript ?? ""} />
        </Text>
      </Paper>
    </div>
  );
};

const UserMessage = ({ markdown }: { markdown?: string }) => {
  return (
    <div className="flex justify-end">
      <Paper className="rounded-t-xl rounded-bl-xl p-4 shadow-sm">
        <Text className="prose text-sm">
          <Markdown content={markdown ?? ""} />
        </Text>
      </Paper>
    </div>
  );
};

const SystemMessage = ({
  markdown,
  title,
}: {
  markdown?: string;
  title?: ReactNode;
}) => {
  return (
    <div className="flex justify-start">
      <Paper
        bg="transparent"
        className="rounded-t-xl rounded-br-xl border border-slate-200 p-4 shadow-sm"
      >
        <Stack>
          {!!title && title}
          <Text className="prose text-sm">
            <Markdown content={markdown ?? ""} />
          </Text>
        </Stack>
      </Paper>
    </div>
  );
};

const SpikeMessage = ({ message }: { message: ConversationReply }) => {
  if (message.type === "assistant_reply") {
    return (
      <SystemMessage
        markdown={message.content_text ?? ""}
        title={
          <Group>
            <Text className="font-semibold">
              <Trans>ECHO!</Trans>
            </Text>
            <Logo hideTitle h="20px" />
          </Group>
        }
      />
    );
  }
  // if (message.type === "object") {
  //   return <SpikeObjectMessage message={message} />;
  // }
  // if (message.type === "user_audio") {
  //   return null;
  // }
  // return <></>;

  return null;
};

const combineUserChunks = (
  chunks: { type: "user_chunk"; timestamp: Date; data: TConversationChunk }[],
) => {
  return {
    type: "user_chunk" as const,
    timestamp: chunks[0].timestamp,
    data: {
      ...chunks[0].data,
      transcript: chunks.map((c) => c.data.transcript).join("..."),
    },
  };
};

const ParticipantBody = ({
  projectId,
  conversationId,
  viewResponses = false,
  children,
  interleaveMessages = true,
}: PropsWithChildren<{
  projectId: string;
  conversationId: string;
  viewResponses?: boolean;
  interleaveMessages?: boolean;
}>) => {
  const [ref] = useAutoAnimate();
  const [chatRef] = useAutoAnimate();
  const bottomRef = useRef<HTMLDivElement>(null);

  const projectQuery = useParticipantProjectById(projectId);
  const chunksQuery = useConversationChunksQuery(projectId, conversationId);
  const repliesQuery = useConversationRepliesQuery(conversationId);

  console.log(projectQuery.data?.is_get_reply_enabled, "  ===> data")

  const combinedMessages = useMemo(() => {
    const userChunks = (chunksQuery.data ?? []).map((chunk) => ({
      type: "user_chunk" as const,
      timestamp: new Date(chunk.timestamp),
      data: chunk,
    }));

    const replies = (repliesQuery.data ?? [])
      .filter((m) => ["assistant_reply"].includes(m.type ?? ""))
      .map((m) => ({
        type: "assistant_chunk" as const,
        timestamp: new Date(m.date_created ?? ""),
        data: m,
      }));

    const allMessages = [...userChunks, ...replies].sort(
      (a, b) => a.timestamp.getTime() - b.timestamp.getTime(),
    );

    const combinedResult = [];
    let currentUserChunks = [];

    for (let i = 0; i < allMessages.length; i++) {
      const message = allMessages[i];
      if (message.type === "user_chunk") {
        currentUserChunks.push(message);
      } else {
        if (currentUserChunks.length > 0) {
          if (currentUserChunks.length > 1) {
            combinedResult.push(combineUserChunks(currentUserChunks));
          } else {
            combinedResult.push(currentUserChunks[0]);
          }
          currentUserChunks = [];
        }
        combinedResult.push(message);
      }
    }
    if (currentUserChunks.length > 0) {
      if (currentUserChunks.length > 1) {
        combinedResult.push(combineUserChunks(currentUserChunks));
      } else {
        combinedResult.push(currentUserChunks[0]);
      }
    }

    return combinedResult;
  }, [chunksQuery.data, repliesQuery.data, interleaveMessages]);

  const [opened, { open, close }] = useDisclosure(false);

  return (
    <Stack ref={ref} className="max-h-full">
      <h2 className="text-center text-3xl">
        <Trans>Welcome</Trans>
      </h2>
      <img
        className="w-full animate-pulse object-contain duration-1000"
        src={WelcomeImage}
      />
      {projectQuery.data && (
        <Stack ref={chatRef} py="md" pb={9}>
          <Title order={3}>
            {projectQuery.data.default_conversation_title}
          </Title>

          {projectQuery.data.default_conversation_description && (
            <SystemMessage
              markdown={
                projectQuery.data.default_conversation_description ?? ""
              }
            />
          )}

          <SystemMessage
            markdown={t`Please record your response by clicking the "Start Recording" button below. You may also choose to respond in text by clicking the text icon.`}
          />

          {children}

          {interleaveMessages ? (
            <Stack gap="sm">
              {combinedMessages.map((message, index) => (
                <div key={index}>
                  {message.type === "user_chunk" ? (
                    <UserChunkMessage chunk={message.data} />
                  ) : (
                    <SpikeMessage message={message.data} />
                  )}
                </div>
              ))}
            </Stack>
          ) : (
            <>
              {viewResponses ? (
                <div className="flex justify-end">
                  <Stack gap="sm">
                    {chunksQuery.data
                      ?.sort(
                        (a, b) =>
                          new Date(a.timestamp).getTime() -
                          new Date(b.timestamp).getTime(),
                      )
                      .map((chunk) => (
                        <UserChunkMessage key={chunk.id} chunk={chunk} />
                      ))}
                  </Stack>
                </div>
              ) : (
                <>
                  {chunksQuery.data && chunksQuery.data.length > 0 && (
                    <div className="flex justify-end">
                      <Button variant="transparent" onClick={open}>
                        <Trans>View your responses</Trans>
                      </Button>
                    </div>
                  )}
                  <Modal
                    opened={opened}
                    onClose={close}
                    size="lg"
                    title={t`Your responses`}
                  >
                    <div style={{ maxHeight: "70vh", overflowY: "auto" }}>
                      <Stack gap="sm">
                        {chunksQuery.data
                          ?.sort(
                            (a, b) =>
                              new Date(a.timestamp).getTime() -
                              new Date(b.timestamp).getTime(),
                          )
                          .map((chunk) => (
                            <UserChunkMessage key={chunk.id} chunk={chunk} />
                          ))}
                      </Stack>
                    </div>
                  </Modal>
                </>
              )}
              <Stack gap="sm">
                {repliesQuery.data?.map((msg) => (
                  <SpikeMessage key={msg.id} message={msg} />
                ))}
              </Stack>
            </>
          )}

          <div
            role="presentation"
            ref={bottomRef}
            style={{ float: "left", clear: "both", display: "none" }}
          ></div>
        </Stack>
      )}
    </Stack>
  );
};

// const DEFAULT_REPLY_COOLDOWN = 120; // 2 minutes in seconds
const DEFAULT_REPLY_COOLDOWN = 0; // 2 minutes in seconds

export const ParticipantConversationAudioRoute = () => {
  const { projectId, conversationId } = useParams();
  const projectQuery = useParticipantProjectById(projectId ?? "");
  const conversationQuery = useConversationQuery(projectId, conversationId);
  const chunks = useConversationChunksQuery(projectId, conversationId);
  const uploadChunkMutation = useUploadConversationChunk();

  const onChunk = (chunk: Blob) => {
    uploadChunkMutation.mutate({
      conversationId: conversationId ?? "",
      chunk,
      timestamp: new Date(),
    });
  };

  const audioRecorder = useChunkedAudioRecorder({ onChunk });

  useWakeLock({ obtainWakeLockOnMount: true });

  const {
    startRecording,
    stopRecording,
    isRecording,
    isPaused,
    pauseRecording,
    resumeRecording,
    recordingTime,
    errored,
    loading,
    permissionError,
  } = audioRecorder;

  const [troubleShootingGuideOpened, setTroubleShootingGuideOpened] =
    useState(false);

  const navigate = useI18nNavigate();

  const { iso639_1 } = useLanguage();
  const getReplyMutation = useConversationReplyMutation();

  const [lastReplyTime, setLastReplyTime] = useState<Date | null>(null);

  // Calculate remaining cooldown time
  const getRemainingCooldown = useCallback(() => {
    if (!lastReplyTime) return 0;
    const cooldownSeconds = DEFAULT_REPLY_COOLDOWN;
    const elapsedSeconds = Math.floor(
      (new Date().getTime() - lastReplyTime.getTime()) / 1000,
    );
    return Math.max(0, cooldownSeconds - elapsedSeconds);
  }, [lastReplyTime]);

  const [remainingCooldown, setRemainingCooldown] = useState(0);

  // Update cooldown timer
  useEffect(() => {
    if (!lastReplyTime) return;

    const interval = setInterval(() => {
      const remaining = getRemainingCooldown();
      // setRemainingCooldown(remaining);
      setRemainingCooldown(0);

      if (remaining <= 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [lastReplyTime, getRemainingCooldown]);

  const handleCheckMicrophoneAccess = async () => {
    const permissionError = await checkPermissionError();
    if (["granted", "prompt"].includes(permissionError ?? "")) {
      window.location.reload();
    } else {
      alert(
        t`Microphone access is still denied. Please check your settings and try again.`,
      );
    }
  };

  const [showCooldownMessage, setShowCooldownMessage] = useState(false);

  const handleReply = async () => {
    console.log("Echo clicked")
    const remaining = getRemainingCooldown();
    if (remaining > 0) {
      setShowCooldownMessage(true);
      const minutes = Math.floor(remaining / 60);
      const seconds = remaining % 60;
      const timeStr =
        minutes > 0
          ? t`${minutes} minutes and ${seconds} seconds`
          : t`${seconds} seconds`;

      alert(t`Please wait ${timeStr} before requesting another echo.`);
      return;
    }

    try {
      setShowCooldownMessage(false);
      // Wait for pending uploads to complete
      while (uploadChunkMutation.isPending) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      await getReplyMutation.mutateAsync({
        conversationId: conversationId ?? "",
        language: iso639_1,
      });
      setLastReplyTime(new Date());
      // setRemainingCooldown(DEFAULT_REPLY_COOLDOWN);
      setRemainingCooldown(0);
    } catch (error) {
      console.error("Error during echo:", error);
    }
  };

  if (conversationQuery.isLoading || loading || projectQuery.isLoading) {
    return <LoadingOverlay visible />;
  }

  const textModeUrl = `/${projectId}/conversation/${conversationId}/text`;
  const finishUrl = `/${projectId}/conversation/${conversationId}/finish`;

  const handleFinish = async () => {
    if (window.confirm(t`Are you sure you want to finish?`)) {
      await finishConversation(conversationId ?? "");
      navigate(finishUrl);
    }
  };

  return (
    <div className="container mx-auto flex h-full max-w-2xl flex-col">
      {/* modal for permissions error */}
      <Modal
        opened={!!permissionError}
        onClose={() => true}
        centered
        fullScreen
        radius={0}
        transitionProps={{ transition: "fade", duration: 200 }}
        withCloseButton={false}
      >
        <div className="h-full rounded-md bg-white py-4">
          <Stack className="container mx-auto mt-4 max-w-2xl px-2" gap="lg">
            <div className="max-w-prose text-lg">
              <Trans>
                Oops! It looks like microphone access was denied. No worries,
                though! We've got a handy troubleshooting guide for you. Feel
                free to check it out. Once you've resolved the issue, come back
                and visit this page again to check if your microphone is ready.
              </Trans>
            </div>

            <Button
              component="a"
              href="https://dembrane.notion.site/Troubleshooting-Microphone-Permissions-All-Languages-bd340257647742cd9cd960f94c4223bb?pvs=74"
              target="_blank"
              size={troubleShootingGuideOpened ? "lg" : "xl"}
              leftSection={<IconQuestionMark />}
              variant={!troubleShootingGuideOpened ? "filled" : "light"}
              onClick={() => setTroubleShootingGuideOpened(true)}
            >
              <Trans>Open troubleshooting guide</Trans>
            </Button>
            <Divider />
            <Button
              size={!troubleShootingGuideOpened ? "lg" : "xl"}
              leftSection={<IconReload />}
              variant={troubleShootingGuideOpened ? "filled" : "light"}
              onClick={handleCheckMicrophoneAccess}
            >
              <Trans>Check microphone access</Trans>
            </Button>
          </Stack>
        </div>
      </Modal>

      <Box className={clsx("relative flex-grow px-4 py-4 transition-all")}>
        {projectQuery.data && conversationQuery.data && (
          <ParticipantBody
            interleaveMessages={false}
            projectId={projectId ?? ""}
            conversationId={conversationId ?? ""}
          />
        )}

        {/* Show streaming content in a chat bubble */}
        {(getReplyMutation.isStreaming || getReplyMutation.streamingContent) && (
          <div className="flex justify-start">
            <Paper className="rounded-t-xl rounded-br-xl p-4">
              <Stack>
                <Group>
                  <Text className="font-semibold">
                    <Trans>ECHO!</Trans>
                  </Text>
                  <Logo hideTitle h="20px" />
                  {getReplyMutation.isStreaming && (
                    <Loader size="sm" type="dots"/>
                  )}
                </Group>
                <Text className="prose text-sm">
                  <Markdown content={getReplyMutation.streamingContent} />
                </Text>
              </Stack>
            </Paper>
          </div>
        )}
      </Box>

      {!errored && (
        <Stack
          gap="lg"
          className="sticky bottom-0 z-10 w-full border-t border-slate-300 bg-white p-4 shadow-sm"
        >
          {chunks?.data &&
            chunks.data.length > 0 &&
            !!projectQuery.data?.is_get_reply_enabled && (
              <Group>
                <Button
                  fullWidth
                  variant="transparent"
                  size="xl"
                  rightSection={
                    <div className="pl-2">
                      <Logo />
                    </div>
                  }
                  onClick={handleReply}
                  loading={getReplyMutation.isStreaming}
                  loaderProps={{ type: "dots" }}
                >
                  {showCooldownMessage && remainingCooldown > 0 ? (
                    <Text>
                      <Trans>
                        Wait {Math.floor(remainingCooldown / 60)}:
                        {(remainingCooldown % 60).toString().padStart(2, "0")}
                      </Trans>
                    </Text>
                  ) : (
                    <Trans>ECHO!</Trans>
                  )}
                </Button>
              </Group>
            )}

          {/* Recording time indicator */}
          {isRecording && (
            <div className="w-full border-slate-300 bg-white pb-4 pt-2">
              <Group justify="center" align="center">
                {isPaused ? (
                  <IconPlayerPause />
                ) : (
                  <div className="h-4 w-4 animate-pulse rounded-full bg-red-500"></div>
                )}
                <Text className="text-4xl">
                  {Math.floor(recordingTime / 3600) > 0 && (
                    <>
                      {Math.floor(recordingTime / 3600)
                        .toString()
                        .padStart(2, "0")}
                      :
                    </>
                  )}
                  {Math.floor((recordingTime % 3600) / 60)
                    .toString()
                    .padStart(2, "0")}
                  :{(recordingTime % 60).toString().padStart(2, "0")}
                </Text>
              </Group>
            </div>
          )}

          <Group justify="center">
            {!isRecording && (
              <>
                <Group className="w-full">
                  <Button
                    size="xl"
                    rightSection={<IconMicrophone />}
                    onClick={startRecording}
                    className="flex-grow"
                  >
                    <Trans>Start Recording</Trans>
                  </Button>

                  <I18nLink to={textModeUrl}>
                    <ActionIcon component="a" size="60" variant="outline">
                      <IconTextCaption />
                    </ActionIcon>
                  </I18nLink>

                  {!isRecording && chunks?.data && chunks.data.length > 0 && (
                    <Button
                      size="xl"
                      onClick={handleFinish}
                      component="a"
                      variant="light"
                      rightSection={<IconCheck />}
                    >
                      Finish
                    </Button>
                  )}
                </Group>
              </>
            )}

            {isRecording && (
              <>
                {isPaused ? (
                  <Button
                    className="flex-1"
                    size="xl"
                    rightSection={<IconPlayerPlay size={16} />}
                    onClick={resumeRecording}
                  >
                    <Trans>Resume</Trans>
                  </Button>
                ) : (
                  <Button
                    className="flex-1"
                    size="xl"
                    rightSection={<IconPlayerPause size={16} />}
                    onClick={pauseRecording}
                  >
                    <Trans>Pause</Trans>
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="xl"
                  rightSection={<IconPlayerStop size={16} />}
                  onClick={() => {
                    stopRecording();
                  }}
                >
                  <Trans>Stop</Trans>
                </Button>
              </>
            )}
          </Group>
        </Stack>
      )}
    </div>
  );
};

export const ParticipantConversationTextRoute = () => {
  const { projectId, conversationId } = useParams();
  const projectQuery = useParticipantProjectById(projectId ?? "");
  const conversationQuery = useConversationQuery(projectId, conversationId);
  const chunks = useConversationChunksQuery(projectId, conversationId);
  const uploadChunkMutation = useUploadConversationTextChunk();

  const [text, setText] = useState("");

  const onChunk = () => {
    if (!text || text.trim() === "") {
      return;
    }

    uploadChunkMutation.mutate({
      conversationId: conversationId ?? "",
      timestamp: new Date(),
      content: text.trim(),
    });

    setText("");
  };

  const navigate = useI18nNavigate();

  const audioModeUrl = `/${projectId}/conversation/${conversationId}`;
  const finishUrl = `/${projectId}/conversation/${conversationId}/finish`;

  const handleFinish = () => {
    if (window.confirm(t`Are you sure you want to finish?`)) {
      navigate(finishUrl);
    }
  };

  if (conversationQuery.isLoading || projectQuery.isLoading) {
    return <LoadingOverlay visible />;
  }

  return (
    <div className="container mx-auto flex h-full max-w-2xl flex-col">
      <Box className={clsx("relative flex-grow px-4 py-4 transition-all")}>
        {projectQuery.data && conversationQuery.data && (
          <ParticipantBody
            viewResponses
            projectId={projectId ?? ""}
            conversationId={conversationId ?? ""}
          />
        )}
      </Box>

      <Stack className="sticky bottom-0 z-10 w-full border-t border-slate-300 bg-white p-4 shadow-sm">
        <textarea
          className="h-32 w-full rounded-md border border-slate-300 p-4"
          placeholder={t`Type your response here`}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Group className="w-full">
          <Button
            size="xl"
            rightSection={<IconUpload />}
            onClick={onChunk}
            loading={uploadChunkMutation.isPending}
            className="flex-grow"
          >
            <Trans>Submit</Trans>
          </Button>

          <I18nLink to={audioModeUrl}>
            <ActionIcon component="a" variant="outline" size="60">
              <IconMicrophone />
            </ActionIcon>
          </I18nLink>
          {text.trim() == "" && chunks.data && chunks.data.length > 0 && (
            <Button
              size="xl"
              onClick={handleFinish}
              component="a"
              variant="light"
              rightSection={<IconCheck />}
            >
              <Trans>Finish</Trans>
            </Button>
          )}
        </Group>
      </Stack>
    </div>
  );
};
