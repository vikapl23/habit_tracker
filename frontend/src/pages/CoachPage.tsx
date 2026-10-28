import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Send,
  Trash2,
  Sparkles,
  AlertCircle,
  X,
  Loader2,
} from 'lucide-react';
import { BottomNavigation } from '../components/BottomNavigation';
import { coachApi } from '../api/coach';
import { ChatMessage } from '../types/coach';
import { ApiError } from '../api/client';
import { getErrorMessage } from '../utils/errorUtils';

const STARTER_QUESTIONS = [
  'How am I doing this week?',
  'Help me build a morning routine',
  'Suggest habits for better sleep',
  'I want to start reading 10 pages daily',
];

export const CoachPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [remainingMessages, setRemainingMessages] = useState<number>(20);
  const [dailyLimit, setDailyLimit] = useState<number>(20);
  const [inputContent, setInputContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showClearModal, setShowClearModal] = useState<boolean>(false);
  const [isClearing, setIsClearing] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({
      behavior: smooth ? 'smooth' : 'auto',
    });
  };

  useEffect(() => {
    let isMounted = true;
    const fetchMessages = async () => {
      try {
        setIsLoading(true);
        setErrorMessage(null);
        const data = await coachApi.getMessages();
        if (isMounted) {
          setMessages(data.results || []);
          setRemainingMessages(data.remaining_messages);
          setDailyLimit(data.daily_limit);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setErrorMessage(
            getErrorMessage(err, 'Failed to load coach messages. Please check your connection.')
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchMessages();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    scrollToBottom(false);
  }, [messages, isSending]);

  const handleSendMessage = async (textToSend?: string) => {
    const content = (textToSend || inputContent).trim();
    if (!content || isSending || remainingMessages <= 0) {
      return;
    }

    if (!textToSend) {
      setInputContent('');
    }
    setErrorMessage(null);
    setIsSending(true);

    try {
      const response = await coachApi.sendMessage(content);
      setMessages((prev) => [
        ...prev,
        response.user_message,
        response.assistant_message,
      ]);
      setRemainingMessages(response.remaining_messages);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 429) {
        setRemainingMessages(0);
      }
      setErrorMessage(getErrorMessage(err, 'Failed to send message. Please try again.'));
    } finally {
      setIsSending(false);
    }
  };

  const handleClearChat = async () => {
    try {
      setIsClearing(true);
      await coachApi.clearMessages();
      setMessages([]);
      setShowClearModal(false);
    } catch (err: unknown) {
      setErrorMessage(
        getErrorMessage(err, 'Failed to clear conversation history.')
      );
    } finally {
      setIsClearing(false);
    }
  };

  const formatMessageTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="max-w-[420px] mx-auto min-h-screen bg-slate-50 flex flex-col pb-36">
      {/* Top Navigation Header */}
      <header className="sticky top-0 z-20 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 py-3 flex items-center justify-between shadow-xs">
        <div className="flex items-center space-x-2">
          <div className="w-9 h-9 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h1 className="text-base font-bold text-slate-800">AI Habit Coach</h1>
              <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
            </div>
            <p className="text-xs text-slate-500 font-medium">
              {remainingMessages} / {dailyLimit} left today
            </p>
          </div>
        </div>

        <button
          type="button"
          data-testid="coach-clear-button"
          onClick={() => setShowClearModal(true)}
          disabled={messages.length === 0 || isLoading}
          className="p-2 text-slate-400 hover:text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg hover:bg-slate-100 transition-colors"
          title="Clear conversation"
          aria-label="Clear conversation"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </header>

      {/* Main Content & Message Stream */}
      <main className="flex-1 p-4 space-y-4">
        {errorMessage && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start space-x-2 text-xs text-red-700">
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p>{errorMessage}</p>
            </div>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              className="text-red-400 hover:text-red-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {isLoading ? (
          <div
            data-testid="coach-loading"
            className="flex flex-col items-center justify-center py-20 space-y-3"
          >
            <div className="w-8 h-8 rounded-full border-3 border-blue-600 border-t-transparent animate-spin" />
            <p className="text-xs font-medium text-slate-500">Connecting to coach...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="py-6 space-y-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-5 text-center shadow-xs space-y-3">
              <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-sm">
                <Bot className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-800">
                  Hi, I'm your AI Habit Coach! 👋
                </h2>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  I can review your streaks, answer questions about your progress, and help you build strong daily routines.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
                Suggested questions
              </p>
              <div className="flex flex-col space-y-2">
                {STARTER_QUESTIONS.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => handleSendMessage(question)}
                    disabled={isSending || remainingMessages <= 0}
                    className="w-full text-left p-3 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/50 hover:text-blue-700 transition-colors shadow-xs flex items-center justify-between group disabled:opacity-50"
                  >
                    <span>{question}</span>
                    <Sparkles className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-xs ${
                      isUser
                        ? 'bg-blue-600 text-white rounded-tr-none'
                        : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                  </div>
                  <span className="text-[10px] text-slate-400 px-1 mt-1">
                    {formatMessageTime(msg.created_at)}
                  </span>
                </div>
              );
            })}

            {isSending && (
              <div className="flex flex-col items-start space-y-1">
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-xs flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600 animate-bounce" />
                  <span
                    className="w-2 h-2 rounded-full bg-blue-600 animate-bounce"
                    style={{ animationDelay: '0.15s' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-blue-600 animate-bounce"
                    style={{ animationDelay: '0.3s' }}
                  />
                </div>
                <span className="text-[10px] text-slate-400 px-1">Coach is typing...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Floating Bottom Input Bar */}
      <footer className="fixed bottom-16 left-0 right-0 max-w-[420px] mx-auto bg-white/95 backdrop-blur-md border-t border-slate-200 px-3 py-2.5 z-20 shadow-lg">
        {remainingMessages === 0 && (
          <div className="mb-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-center text-xs text-amber-700">
            Daily limit reached (20/20). Resets at midnight.
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center space-x-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={inputContent}
              onChange={(e) => setInputContent(e.target.value)}
              placeholder={
                remainingMessages === 0
                  ? 'Daily limit reached'
                  : 'Ask your coach about habits or routines...'
              }
              disabled={isSending || remainingMessages === 0}
              maxLength={1000}
              className="w-full bg-slate-100 border border-slate-200 rounded-full px-4 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all disabled:opacity-50 disabled:bg-slate-200"
            />
            {inputContent.length > 0 && (
              <span
                className={`absolute right-3 top-2.5 text-[10px] ${
                  inputContent.length > 950 ? 'text-red-500 font-bold' : 'text-slate-400'
                }`}
              >
                {inputContent.length}/1000
              </span>
            )}
          </div>
          <button
            type="submit"
            data-testid="coach-send-button"
            disabled={!inputContent.trim() || isSending || remainingMessages === 0}
            className="w-10 h-10 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-colors shrink-0"
            aria-label="Send message"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4 ml-0.5" />
            )}
          </button>
        </form>
      </footer>

      {/* Confirmation Modal for Clear Chat */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center space-x-3 text-slate-800">
              <div className="w-10 h-10 rounded-full bg-red-50 border border-red-100 flex items-center justify-center text-red-600 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold">Clear conversation?</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  This will delete all messages and cancel any pending actions.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setShowClearModal(false)}
                disabled={isClearing}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleClearChat}
                disabled={isClearing}
                className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {isClearing ? 'Clearing...' : 'Clear chat'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Bottom Navigation */}
      <BottomNavigation />
    </div>
  );
};
