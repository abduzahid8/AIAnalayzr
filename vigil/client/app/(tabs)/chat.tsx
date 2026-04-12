import { useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import FontAwesome from '@expo/vector-icons/FontAwesome';

import { useVigil } from '@/src/context/VigilContext';
import { colors, getTierColor } from '@/src/theme';

const SUGGESTED_QUESTIONS = [
  'What should I do first this week?',
  'Should we hedge our positions now?',
  'How does our risk compare to competitors?',
  'Is this a good time to raise funding?',
  'What\u2019s our biggest blind spot?',
  'Break down the top risk theme for me.',
];

export default function AdvisorScreen() {
  const { analysis, chatMessages, isSendingChat, lastError, sendChat, sessionId } = useVigil();
  const [message, setMessage] = useState('');
  const scrollRef = useRef<ScrollView>(null);

  const chatDisabled = useMemo(
    () => !sessionId || !analysis || isSendingChat || !message.trim(),
    [analysis, isSendingChat, message, sessionId],
  );

  const handleSend = async (text?: string) => {
    const trimmed = (text ?? message).trim();
    if (!trimmed) return;
    setMessage('');
    await sendChat(trimmed);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const showSuggestions = Boolean(sessionId && analysis && chatMessages.length < 4);

  return (
    <KeyboardAvoidingView
      style={s.screen}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <ScrollView ref={scrollRef} contentContainerStyle={s.content}>
        {/* ── Session Header ───────────────────────────────────────── */}
        {analysis ? (
          <>
            <View style={s.sessionCard}>
              <View style={s.sessionTop}>
                <View style={s.sessionIconWrap}>
                  <FontAwesome name="comments-o" size={20} color={colors.accent} />
                </View>
                <View style={s.sessionInfo}>
                  <Text style={s.sessionEyebrow}>STRATEGIC ADVISOR</Text>
                  <Text style={s.sessionCompany}>{analysis.company}</Text>
                </View>
                <View style={s.sessionTierBadge}>
                  <Text style={[s.sessionTierText, { color: getTierColor(analysis.risk_tier) }]}>
                    {Math.round(analysis.risk_score)} {analysis.risk_tier}
                  </Text>
                </View>
              </View>
              <Text style={s.sessionSummary}>{analysis.executive_summary}</Text>
              <View style={s.sessionMeta}>
                <View style={s.sessionPill}>
                  <FontAwesome name="line-chart" size={10} color={colors.textMuted} />
                  <Text style={s.sessionPillText}>{analysis.market_mode}</Text>
                </View>
                <View style={s.sessionPill}>
                  <FontAwesome name="calendar" size={10} color={colors.textMuted} />
                  <Text style={s.sessionPillText}>{analysis.planning_window || '~30 days'}</Text>
                </View>
              </View>
            </View>
            <View style={s.contextCard}>
              <Text style={s.contextEyebrow}>SESSION SNAPSHOT</Text>
              <Text style={s.contextTitle}>What the advisor is allowed to use</Text>
              <Text style={s.contextBody}>
                Answers are grounded in the same JSON payload you reviewed on Analyze: headline score
                and tier, executive summary, risk themes, cascades, stress tests, and the latest signal
                feed. It does not invent new market prices.
              </Text>
              <Text style={s.contextBullet}>
                • Session id {analysis.session_id.slice(0, 8)}… ties this chat to that exact run.
              </Text>
              <Text style={s.contextBullet}>
                • Confidence band{' '}
                {(analysis.confidence_interval ?? [analysis.risk_score, analysis.risk_score])
                  .map((n) => n.toFixed(1))
                  .join(' – ')}{' '}
                — ask the advisor how to tighten controls when the band is wide.
              </Text>
              <Text style={s.contextBullet}>
                • Entropy {analysis.entropy_factor?.toFixed(3) ?? '—'} / divergence{' '}
                {analysis.divergence_index?.toFixed(3) ?? '—'} — use these when you need a story
                about conflicting data.
              </Text>
            </View>
          </>
        ) : (
          <View style={s.emptyCard}>
            <View style={s.emptyIconWrap}>
              <FontAwesome name="comments-o" size={32} color={colors.textDim} />
            </View>
            <Text style={s.emptyTitle}>No Active Session</Text>
            <Text style={s.emptyBody}>
              Run a risk analysis on the Analyze tab first. The advisor uses your company profile,
              risk score, and playbook results to answer strategic questions.
            </Text>
            <View style={s.emptyFeatures}>
              <FeaturePill icon="question-circle" text="Ask strategic questions" />
              <FeaturePill icon="lightbulb-o" text="Get tailored recommendations" />
              <FeaturePill icon="shield" text="Explore risk mitigation paths" />
            </View>
          </View>
        )}

        {/* ── Error Banner ─────────────────────────────────────────── */}
        {lastError ? (
          <View style={s.errorCard}>
            <FontAwesome name="exclamation-triangle" size={14} color={colors.accent} />
            <Text style={s.errorText}>{lastError}</Text>
          </View>
        ) : null}

        {/* ── Suggested Questions ──────────────────────────────────── */}
        {showSuggestions && (
          <View style={s.suggestionsCard}>
            <Text style={s.suggestionsTitle}>Try asking...</Text>
            <View style={s.suggestionsGrid}>
              {SUGGESTED_QUESTIONS.map((q) => (
                <Pressable
                  key={q}
                  accessibilityRole="button"
                  accessibilityLabel={`Ask: ${q}`}
                  style={({ pressed }) => [s.suggestionChip, pressed && s.suggestionChipPressed]}
                  onPress={() => handleSend(q)}
                  disabled={isSendingChat}
                >
                  <Text style={s.suggestionText}>{q}</Text>
                  <FontAwesome name="arrow-right" size={10} color={colors.accent} />
                </Pressable>
              ))}
            </View>
          </View>
        )}

        {/* ── Messages ─────────────────────────────────────────────── */}
        <View style={s.messages}>
          {chatMessages.map((item) => {
            const isUser = item.role === 'user';
            return (
              <View
                key={item.id}
                style={[s.bubble, isUser ? s.userBubble : s.assistantBubble]}
              >
                {!isUser && (
                  <View style={s.bubbleAvatar}>
                    <FontAwesome name="shield" size={12} color={colors.accent} />
                  </View>
                )}
                <View style={[s.bubbleContent, isUser ? s.userContent : s.assistantContent]}>
                  <Text style={s.bubbleText}>{item.content}</Text>
                  {item.meta ? (
                    <View style={s.bubbleMetaRow}>
                      <FontAwesome name="bar-chart" size={10} color={colors.textDim} />
                      <Text style={s.bubbleMeta}>{item.meta}</Text>
                    </View>
                  ) : null}
                </View>
              </View>
            );
          })}

          {isSendingChat && (
            <View style={[s.bubble, s.assistantBubble]}>
              <View style={s.bubbleAvatar}>
                <FontAwesome name="shield" size={12} color={colors.accent} />
              </View>
              <View style={[s.bubbleContent, s.assistantContent]}>
                <Text style={s.typingDots}>Thinking...</Text>
              </View>
            </View>
          )}
        </View>
      </ScrollView>

      {/* ── Composer ───────────────────────────────────────────────── */}
      <View style={s.composer}>
        <TextInput
          accessibilityLabel="Type your question for the strategic advisor"
          placeholder={
            sessionId
              ? 'Ask about risks, strategy, timing, hiring, funding...'
              : 'Run an analysis first to enable the advisor.'
          }
          placeholderTextColor={colors.textDim}
          style={s.composerInput}
          value={message}
          onChangeText={setMessage}
          editable={Boolean(sessionId) && !isSendingChat}
          multiline
          onSubmitEditing={() => !chatDisabled && handleSend()}
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Send message"
          disabled={chatDisabled}
          onPress={() => handleSend()}
          style={({ pressed }) => [
            s.sendButton,
            chatDisabled && s.buttonDisabled,
            pressed && !chatDisabled ? s.buttonPressed : null,
          ]}
        >
          <FontAwesome
            name={isSendingChat ? 'hourglass-half' : 'paper-plane'}
            size={16}
            color={colors.background}
          />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function FeaturePill({ icon, text }: { icon: React.ComponentProps<typeof FontAwesome>['name']; text: string }) {
  return (
    <View style={s.featurePill}>
      <FontAwesome name={icon} size={12} color={colors.accent} />
      <Text style={s.featurePillText}>{text}</Text>
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: {
    gap: 16,
    padding: 16,
    paddingBottom: 200,
    width: '100%',
    maxWidth: 1080,
    alignSelf: 'center',
  },

  // Session Card
  sessionCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 22,
    padding: 20,
    gap: 12,
  },
  sessionTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  sessionIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.accentMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sessionInfo: { flex: 1, gap: 2 },
  sessionEyebrow: {
    color: colors.accent,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
  },
  sessionCompany: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  sessionTierBadge: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: colors.accentMuted,
  },
  sessionTierText: {
    fontSize: 13,
    fontWeight: '900',
  },
  sessionSummary: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
  },
  sessionMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  sessionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.surfaceAlt,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  sessionPillText: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
  },

  contextCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
    gap: 8,
  },
  contextEyebrow: {
    color: colors.accent,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
  },
  contextTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '800',
  },
  contextBody: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  contextBullet: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  },

  // Empty State
  emptyCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 22,
    padding: 32,
    alignItems: 'center',
    gap: 14,
  },
  emptyIconWrap: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '900',
  },
  emptyBody: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
    maxWidth: 400,
  },
  emptyFeatures: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: 4,
  },
  featurePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.accentMuted,
    borderColor: colors.accent,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  featurePillText: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: '700',
  },

  // Suggestions
  suggestionsCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 18,
    gap: 12,
  },
  suggestionsTitle: {
    color: colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
  },
  suggestionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  suggestionChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  suggestionChipPressed: { opacity: 0.6, backgroundColor: colors.surfaceAlt },
  suggestionText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '600',
  },

  // Messages
  messages: { gap: 12 },
  bubble: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    maxWidth: '100%',
  },
  assistantBubble: { alignSelf: 'flex-start' },
  userBubble: { alignSelf: 'flex-end', flexDirection: 'row-reverse' },
  bubbleAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.accentMuted,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  bubbleContent: {
    maxWidth: '85%',
    borderRadius: 18,
    padding: 14,
  },
  assistantContent: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
  },
  userContent: {
    backgroundColor: colors.accentMuted,
    borderColor: 'rgba(0,229,160,0.2)',
    borderWidth: 1,
  },
  bubbleText: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 22,
  },
  bubbleMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  bubbleMeta: {
    color: colors.textDim,
    fontSize: 11,
    fontWeight: '700',
  },
  typingDots: {
    color: colors.textMuted,
    fontSize: 14,
    fontStyle: 'italic',
  },

  // Composer
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
    backgroundColor: colors.surface,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    padding: 14,
  },
  composerInput: {
    flex: 1,
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderRadius: 18,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    maxHeight: 120,
    minHeight: 44,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: { opacity: 0.35 },
  buttonPressed: { opacity: 0.7 },

  // Error
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
  },
  errorText: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20,
    flex: 1,
  },
});
