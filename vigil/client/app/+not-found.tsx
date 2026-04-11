import { Link, Stack } from 'expo-router';
import { StyleSheet } from 'react-native';

import { Text, View } from 'react-native';

import { colors } from '@/src/theme';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Not found' }} />
      <View style={styles.container}>
        <Text style={styles.title}>This route does not exist.</Text>
        <Text style={styles.subtitle}>Go back to the analysis dashboard and continue from there.</Text>

        <Link href="/" style={styles.link}>
          <Text style={styles.linkText}>Back to Vigil</Text>
        </Link>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: colors.background,
    justifyContent: 'center',
    padding: 20,
    gap: 12,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '800',
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 22,
    maxWidth: 420,
    textAlign: 'center',
  },
  link: {
    marginTop: 15,
    paddingVertical: 15,
  },
  linkText: {
    color: colors.accent,
    fontSize: 15,
    fontWeight: '700',
  },
});
