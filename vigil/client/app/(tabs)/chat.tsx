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
import { colors, fonts, getTierColor } from '@/src/theme';

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
        {analysis ? (
          <>
            <View style={s.sessionCard}>
              <View style={s.goldRule} />
              <View style={s.sessionTop}>
                <View style={s.sessionIconWrap}>
                  <FontAwesome name="comments-o" size={18} color={colors.gold} />
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
                  <Text style={s.sessionPillText}>{analysis.market_mode}</Text>
                </View>
                <View style={s.sessionPill}>
                  <Text style={s.sessionPillText}>{analysis.planning_window || '~30 days'}</Text>
                </View>
              </View>
            </View>

            <View style={s.contextCard}>
              <Text style={s.contextEyebrow}>SESSION CONTEXT</Text>
              <Text style={s.contextBody}>
                Answers are grounded in the analysis snapshot — headline score, themes, cascades,
                stress tests, and the signal feed. Session {analysis.session_id.slice(0, 8)}…
              </Text>
            </View>
          </>
        ) : (
          <View style={s.emptyCard}>
            <View style={s.emptyIconWrap}>
              <FontAwesome name="comments-o" size={28} color={colors.textDim} />
            </View>
            <Text style={s.emptyTitle}>No Active Session</Text>
            <Text style={s.emptyBody}>
              Run a risk analysis on the Analyze tab first. The advisor uses your company profile,
              risk score, and playbook to answer strategic questions.
            </Text>
            <View style={s.emptyFeatures}>
              <FeaturePill icon="question-circle" text="Strategic questions" />
              <FeaturePill icon="lightbulb-o" text="Tailored advice" />
              <FeaturePill icon="shield" text="Mitigation paths" />
            </View>
          </View>
        )}

        {lastError ? (
          <View style={s.errorCard}>
            <FontAwesome name="exclamation-triangle" size={13} color={colors.danger} />
            <Text style={s.errorText}>{lastError}</Text>
          </View>
        ) : null}

        {showSuggestions && (
          <View style={s.suggestionsCard}>
            <Text style={s.suggestionsTitle}>TRY ASKING</Text>
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
                  <FontAwesome name="long-arrow-right" size={10} color={colors.gold} />
                </Pressable>
              ))}
            </View>
          </View>
        )}

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
                    <FontAwesome name="shield" size={11} color={colors.gold} />
                  </View>
                )}
                <View style={[s.bubbleContent, isUser ? s.userContent : s.assistantContent]}>
                  <Text style={s.bubbleText}>{item.content}</Text>
                  {item.meta ? (
                    <View style={s.bubbleMetaRow}>
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
                <FontAwesome name="shield" size={11} color={colors.gold} />
              </View>
              <View style={[s.bubbleContent, s.assistantContent]}>
                <Text style={s.typingText}>Thinking…</Text>
              </View>
            </View>
          )}
        </View>
      </ScrollView>

      <View style={s.composer}>
        <TextInput
          accessibilityLabel="Type your question for the strategic advisor"
          placeholder={
            sessionId
              ? 'Ask about risks, strategy, timing…'
              : 'Run an analysis first.'
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
            size={14}
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
      <FontAwesome name={icon} size={11} color={colors.gold} />
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
    maxWidth: 960,
    alignSelf: 'center',
  },

  goldRule: {
    height: 2,
    backgroundColor: colors.gold,
    marginBottom: 8,
  },

  // Session Card
  sessionCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 20,
    gap: 12,
  },
  sessionTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  sessionIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 4,
    backgroundColor: colors.goldMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sessionInfo: { flex: 1, gap: 2 },
  sessionEyebrow: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 9,
    letterSpacing: 3,
  },
  sessionCompany: {
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 20,
  },
  sessionTierBadge: {
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: colors.surfaceRaised,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sessionTierText: {
    fontFamily: fonts.monoBold,
    fontSize: 12,
  },
  sessionSummary: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 21,
  },
  sessionMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  sessionPill: {
    backgroundColor: colors.surfaceRaised,
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  sessionPillText: {
    fontFamily: fonts.mono,
    color: colors.textSecondary,
    fontSize: 11,
  },

  // Context
  contextCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 16,
    gap: 8,
  },
  contextEyebrow: {
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 9,
    letterSpacing: 3,
  },
  contextBody: {
    fontFamily: fonts.sans,
    color: colors.textDim,
    fontSize: 12,
    lineHeight: 18,
  },

  // Empty State
  emptyCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 32,
    alignItems: 'center',
    gap: 14,
  },
  emptyIconWrap: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  emptyTitle: {
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 22,
  },
  emptyBody: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
    maxWidth: 380,
  },
  emptyFeatures: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: 8,
  },
  featurePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.goldMuted,
    borderColor: colors.gold,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  featurePillText: {
    fontFamily: fonts.mono,
    color: colors.gold,
    fontSize: 11,
  },

  // Suggestions
  suggestionsCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: 16,
    gap: 12,
  },
  suggestionsTitle: {
    fontFamily: fonts.monoBold,
    color: colors.textDim,
    fontSize: 10,
    letterSpacing: 2,
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
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  suggestionChipPressed: { opacity: 0.6 },
  suggestionText: {
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 13,
  },

  // Messages
  messages: { gap: 14 },
  bubble: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    maxWidth: '100%',
  },
  assistantBubble: { alignSelf: 'flex-start' },
  userBubble: { alignSelf: 'flex-end', flexDirection: 'row-reverse' },
  bubbleAvatar: {
    width: 26,
    height: 26,
    borderRadius: 4,
    backgroundColor: colors.goldMuted,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  bubbleContent: {
    maxWidth: '85%',
    borderRadius: 6,
    padding: 14,
  },
  assistantContent: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
  },
  userContent: {
    backgroundColor: colors.goldMuted,
    borderColor: colors.goldSubtle,
    borderWidth: 1,
  },
  bubbleText: {
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 14,
    lineHeight: 22,
  },
  bubbleMetaRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  bubbleMeta: {
    fontFamily: fonts.mono,
    color: colors.textDim,
    fontSize: 11,
  },
  typingText: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
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
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: 4,
    borderWidth: 1,
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 14,
    maxHeight: 120,
    minHeight: 44,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 4,
    backgroundColor: colors.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: { opacity: 0.3 },
  buttonPressed: { opacity: 0.7 },

  // Error
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.dangerMuted,
    borderColor: colors.danger,
    borderRadius: 4,
    borderWidth: 1,
    padding: 14,
  },
  errorText: {
    fontFamily: fonts.sans,
    color: colors.text,
    fontSize: 13,
    lineHeight: 20,
    flex: 1,
  },
});
