import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import KakaoProvider from "next-auth/providers/kakao";

// ORCID provider arrives with #11 priority-classifier / #04 monitoring
// sprints — it requires the user to consent to research-context scopes that
// only make sense once those features exist.
export const authOptions: NextAuthOptions = {
  providers: [
    KakaoProvider({
      clientId: process.env.KAKAO_CLIENT_ID ?? "",
      clientSecret: process.env.KAKAO_CLIENT_SECRET ?? "",
    }),
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.provider = account.provider;
      }
      if (profile && "id" in profile) {
        token.providerId = String(profile.id);
      }
      return token;
    },
    async session({ session, token }) {
      // §4.2 — surface the user_id on the session so the backend can scope
      // every cross-domain query to a single namespace.
      if (session.user) {
        (session.user as { id?: string }).id =
          (token.providerId as string | undefined) ?? token.sub ?? "";
      }
      return session;
    },
  },
};
