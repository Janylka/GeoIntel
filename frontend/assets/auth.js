// Thin wrapper around Firebase Auth (Google sign-in + email link).
// Exposes window.geointelAuth with: currentUser, getIdToken(), signInWithGoogle(),
// signOutUser(), onAuthChange(callback). Degrades to a no-op/no-auth mode when
// firebase-config.js has empty values, so public pages keep working without Firebase set up.

const cfg = window.GEOINTEL_FIREBASE_CONFIG || {};
const isConfigured = Boolean(cfg.apiKey && cfg.projectId);

let auth = null;
let currentUser = null;
const listeners = [];

function notify() {
  listeners.forEach((cb) => cb(currentUser));
}

async function init() {
  if (!isConfigured) {
    console.warn(
      "[GeoIntel] Firebase is not configured (frontend/assets/firebase-config.js). " +
        "Sign-in is disabled; public dashboard pages still work."
    );
    return;
  }
  const { initializeApp } = await import(
    "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js"
  );
  const {
    getAuth,
    onAuthStateChanged,
    signInWithPopup,
    GoogleAuthProvider,
    signOut,
    sendSignInLinkToEmail,
    isSignInWithEmailLink,
    signInWithEmailLink,
  } = await import("https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js");

  const app = initializeApp(cfg);
  auth = getAuth(app);

  onAuthStateChanged(auth, (user) => {
    currentUser = user;
    notify();
  });

  if (isSignInWithEmailLink(auth, window.location.href)) {
    const email = window.localStorage.getItem("geointel_email_for_signin");
    if (email) {
      try {
        await signInWithEmailLink(auth, email, window.location.href);
        window.localStorage.removeItem("geointel_email_for_signin");
      } catch (e) {
        console.error("[GeoIntel] Email link sign-in failed:", e);
      }
    }
  }

  window.geointelAuth._googleProvider = new GoogleAuthProvider();
  window.geointelAuth._signInWithPopup = signInWithPopup;
  window.geointelAuth._signOut = signOut;
  window.geointelAuth._sendSignInLinkToEmail = sendSignInLinkToEmail;
}

const readyPromise = init();

window.geointelAuth = {
  isConfigured,
  ready: readyPromise,
  get currentUser() {
    return currentUser;
  },
  async getIdToken() {
    if (!isConfigured || !currentUser) return null;
    return currentUser.getIdToken();
  },
  async signInWithGoogle() {
    if (!isConfigured) throw new Error("Firebase is not configured.");
    await readyPromise;
    await this._signInWithPopup(auth, this._googleProvider);
  },
  async sendEmailLink(email) {
    if (!isConfigured) throw new Error("Firebase is not configured.");
    await readyPromise;
    const actionCodeSettings = {
      url: window.location.href,
      handleCodeInApp: true,
    };
    await this._sendSignInLinkToEmail(auth, email, actionCodeSettings);
    window.localStorage.setItem("geointel_email_for_signin", email);
  },
  async signOutUser() {
    if (!isConfigured) return;
    await readyPromise;
    await this._signOut(auth);
  },
  onAuthChange(cb) {
    listeners.push(cb);
    if (currentUser !== undefined) cb(currentUser);
    return () => {
      const i = listeners.indexOf(cb);
      if (i >= 0) listeners.splice(i, 1);
    };
  },
};
