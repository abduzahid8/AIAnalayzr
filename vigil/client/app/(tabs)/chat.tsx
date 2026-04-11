import { useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { useVigil } from '@/src/context/VigilContext';
import { colors, getTierColor } from '@/src/theme';

export default function AdvisorScreen() {
  const { analysis, chatMessages, isSendingChat, lastError, sendChat, sessionId } = useVigil();
  const [message, setMessage] = useState('');

  const chatDisabled = useMemo(
    () => !sessionId || !analysis || isSendingChat || !message.trim(),
    [analysis, isSendingChat, message, sessionId],
  );

  const handleSend = async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setMessage('');
    await sendChat(trimmed);
  };

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.summaryCard}>
          <Text style={styles.eyebrow}>ADVISOR SESSION</Text>
          {analysis ? (
            <>
              <Text style={styles.summaryTitle}>{analysis.company}</Text>
              <Text style={styles.summaryBody}>{analysis.executive_summary}</Text>
              <View style={styles.summaryRow}>
                <Text style={[styles.scorePill, { color: getTierColor(analysis.risk_tier) }]}>
                  {Math.round(analysis.risk_score)} {analysis.risk_tier}
                </Text>
                <Text style={styles.metaText}>{analysis.market_mode}</Text>
                <Text style={styles.metaText}>{analysis.planning_window || '~30 days'}</Text>
              </View>
            </>
          ) : (
            <>
              <Text style={styles.summaryTitle}>Run an analysis first</Text>
              <Text style={styles.summaryBody}>
                The advisor uses the current company session, risk score, and playbook results.
              </Text>
            </>
          )}
        </View>

        {lastError ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>{lastError}</Text>
          </View>
        ) : null}

        <View style={styles.messagesCard}>
          {chatMessages.map((item) => (
            <View
              key={item.id}
              style={[
                styles.messageBubble,
                item.role === 'user' ? styles.userBubble : styles.assistantBubble,
              ]}>
              <Text style={styles.messageText}>{item.content}</Text>
              {item.meta ? <Text style={styles.messageMeta}>{item.meta}</Text> : null}
            </View>
          ))}
        </View>
      </ScrollView>

      <View style={styles.composer}>
        <TextInput
          placeholder={
            sessionId
              ? 'Ask whether to launch, hire, expand, or hedge based on this analysis.'
              : 'Run an analysis first to enable advisor chat.'
          }
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={message}
          onChangeText={setMessage}
          editable={Boolean(sessionId) && !isSendingChat}
          multiline
        />
        <Pressable
          accessibilityRole="button"
          disabled={chatDisabled}
          onPress={handleSend}
          style={({ pressed }) => [
            styles.sendButton,
            chatDisabled && styles.buttonDisabled,
            pressed && !chatDisabled ? styles.buttonPressed : null,
          ]}>
          <Text style={styles.sendButtonText}>{isSendingChat ? 'Sending...' : 'Send'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    gap: 16,
    padding: 16,
    paddingBottom: 160,
    width: '100%',
    maxWidth: 1080,
    alignSelf: 'center',
  },
  summaryCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 20,
    borderWidth: 1,
    gap: 10,
    padding: 20,
  },
  eyebrow: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
  },
  summaryTitle: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '800',
  },
  summaryBody: {
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 22,
  },
  summaryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  scorePill: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 999,
    fontSize: 13,
    fontWeight: '800',
    overflow: 'hidden',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  metaText: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 999,
    color: colors.text,
    fontSize: 13,
    fontWeight: '700',
    overflow: 'hidden',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  errorCard: {
    backgroundColor: 'rgba(239,68,68,0.12)',
    borderColor: 'rgba(239,68,68,0.35)',
    borderRadius: 14,
    borderWidth: 1,
    padding: 12,
  },
  errorText: {
    color: '#fecaca',
    lineHeight: 20,
  },
  messagesCard: {
    gap: 12,
  },
  messageBubble: {
    borderRadius: 18,
    maxWidth: '100%',
    padding: 14,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: colors.accentMuted,
    borderColor: 'rgba(0,229,160,0.25)',
    borderWidth: 1,
  },
  messageText: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 22,
  },
  messageMeta: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 10,
  },
  composer: {
    backgroundColor: colors.surface,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    gap: 12,
    padding: 16,
  },
  input: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderRadius: 16,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    minHeight: 88,
    paddingHorizontal: 14,
    paddingVertical: 12,
    textAlignVertical: 'top',
  },
  sendButton: {
    alignItems: 'center',
    backgroundColor: colors.accent,
    borderRadius: 14,
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  sendButtonText: {
    color: colors.background,
    fontSize: 15,
    fontWeight: '800',
  },
  buttonDisabled: {
    opacity: 0.45,
  },
  buttonPressed: {
    opacity: 0.8,
  },
});
