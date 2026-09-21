/* Wardrobe AI — shared frontend logic (vanilla + Alpine component factories) */

const WA = {
  USER_KEY: "wa_current_user",

  getUserId() {
    const v = localStorage.getItem(this.USER_KEY);
    return v ? parseInt(v, 10) : null;
  },
  setUserId(id) {
    if (id) localStorage.setItem(this.USER_KEY, id);
    else localStorage.removeItem(this.USER_KEY);
  },

  async request(method, url, body, isForm = false) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      if (isForm) {
        opts.body = body;
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }
    const res = await fetch(url, opts);
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || `Request failed (${res.status})`;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  },
  get(url) { return this.request("GET", url); },
  post(url, body) { return this.request("POST", url, body); },
  put(url, body) { return this.request("PUT", url, body); },
  del(url) { return this.request("DELETE", url); },
  upload(url, formData) { return this.request("POST", url, formData, true); },
};

/* ---------- Global toast bus ---------- */
window._waToast = { show: false, msg: "", type: "" };
function waToast(msg, type = "") {
  window.dispatchEvent(new CustomEvent("wa-toast", { detail: { msg, type } }));
}

/* ---------- Top-bar shell component ---------- */
function appShell() {
  return {
    users: [],
    currentUserId: "",
    toast: { show: false, msg: "", type: "" },
    async init() {
      this.currentUserId = WA.getUserId() || "";
      window.addEventListener("wa-toast", (e) => this.showToast(e.detail));
      try {
        this.users = await WA.get("/api/users");
        // Auto-select first user if none chosen yet.
        if (!this.currentUserId && this.users.length) {
          this.currentUserId = this.users[0].id;
          WA.setUserId(this.users[0].id);
        }
      } catch (e) { /* ignore on splash */ }
    },
    onUserChange() {
      WA.setUserId(this.currentUserId || null);
      location.reload();
    },
    showToast({ msg, type }) {
      this.toast = { show: true, msg, type };
      clearTimeout(this._t);
      this._t = setTimeout(() => (this.toast.show = false), 2600);
    },
  };
}

/* ---------- Reusable multi-select chip helper ---------- */
function toggleInArray(arr, value) {
  const i = arr.indexOf(value);
  if (i === -1) arr.push(value);
  else arr.splice(i, 1);
  return arr;
}
