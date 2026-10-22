import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Mic, Sparkles, User, Bot, RotateCcw } from 'lucide-react';

export default function ChatPanel({
  messages,
  onSendMessage,
  isLoading,
  suggestions,
  onSuggestionClick,
  onReset,
}) {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  // Simulate voice input for in-mall walk
  const handleVoiceToggle = () => {
    if (isListening) {
      setIsListening(false);
      return;
    }
    setIsListening(true);
    // Simulate speech-to-text with sample prompt
    setTimeout(() => {
      setInput('کتونی راحت برای پیاده‌روی تا ۳ میلیون با اسنپ‌پی نزدیک چارسو');
      setIsListening(false);
    }, 2000);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xs">
      {/* Chat Header */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#E8453C] flex items-center justify-center text-white">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-xs text-gray-900">گفتگو با دستیار خرید ترب</h3>
            <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              آنلاین و آماده پاسخگویی
            </span>
          </div>
        </div>

        <button
          onClick={onReset}
          title="شروع مجدد گفتگو"
          className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer text-xs flex items-center gap-1"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline text-[11px]">شروع مجدد</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, idx) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={idx}
              className={`flex items-start gap-2.5 message-enter ${
                isUser ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${
                  isUser
                    ? 'bg-gray-800 text-white'
                    : 'bg-[#E8453C] text-white shadow-xs'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                  isUser
                    ? 'bg-gray-900 text-white rounded-tl-xs'
                    : 'bg-gray-50 text-gray-800 border border-gray-200/80 rounded-tr-xs shadow-2xs'
                }`}
              >
                <div className={`markdown-body max-w-none ${isUser ? 'markdown-body-user' : 'markdown-body-assistant'}`}>
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-gray-400 message-enter">
            <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center text-[#E8453C]">
              <Sparkles className="w-3.5 h-3.5 animate-spin" />
            </div>
            <span className="flex items-center gap-1">
              دستیار در حال جستجو و تحلیل اطلاعات
              <span className="inline-flex gap-0.5">
                <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1 h-1 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions Chips */}
      {suggestions && suggestions.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-100 bg-gray-50/50 flex items-center gap-1.5 overflow-x-auto text-xs">
          <span className="text-[10px] text-gray-400 shrink-0 font-medium">پیشنهاد:</span>
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSuggestionClick(s)}
              className="shrink-0 bg-white hover:bg-red-50 text-gray-700 hover:text-[#E8453C] border border-gray-200 hover:border-red-200 px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-pointer shadow-2xs"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input Bar */}
      <form onSubmit={handleSubmit} className="p-3 bg-white border-t border-gray-200 flex items-center gap-2">
        <button
          type="button"
          onClick={handleVoiceToggle}
          title="ورودی صوتی (مناسب در پاساژ)"
          className={`p-2 rounded-xl transition-all cursor-pointer ${
            isListening
              ? 'bg-red-500 text-white animate-pulse shadow-md shadow-red-200'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
          }`}
        >
          <Mic className="w-4 h-4" />
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isListening ? 'در حال شنیدن صدای شما...' : 'چه محصولی مدنظرتونه؟ بنویسید یا بپرسید...'}
          className="flex-1 text-xs bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-800 placeholder-gray-400 outline-none focus:border-[#E8453C] focus:bg-white transition-all"
        />

        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="bg-[#E8453C] hover:bg-[#d03a31] disabled:opacity-50 text-white p-2.5 rounded-xl transition-colors cursor-pointer disabled:cursor-not-allowed shadow-xs"
        >
          <Send className="w-4 h-4 rotate-180" />
        </button>
      </form>
    </div>
  );
}
