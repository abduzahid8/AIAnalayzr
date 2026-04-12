import { Link, Stack } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { colors, fonts } from '@/src/theme';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Not found' }} />
      <View style={styles.container}>
        <Text style={styles.title}>Route not found.</Text>
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
    fontFamily: fonts.serif,
    color: colors.text,
    fontSize: 24,
  },
  subtitle: {
    fontFamily: fonts.sans,
    color: colors.textSecondary,
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
    fontFamily: fonts.monoBold,
    color: colors.gold,
    fontSize: 13,
    letterSpacing: 1,
  },
});
