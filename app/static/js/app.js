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

function waConfirm(opts) {
  const detail = typeof opts === "string" ? { message: opts } : (opts || {});
  return new Promise((resolve) => {
    window.dispatchEvent(new CustomEvent("wa-confirm", { detail: { ...detail, resolve } }));
  });
}

/* ---------- Top-bar shell component ---------- */
function appShell() {
  return {
    users: [],
    currentUserId: "",
    toast: { show: false, msg: "", type: "" },
    confirmDlg: {
      show: false, title: "", message: "", confirmLabel: "Delete", resolve: null,
    },
    async init() {
      window.addEventListener("wa-toast", (e) => this.showToast(e.detail));
      window.addEventListener("wa-confirm", (e) => this.openConfirm(e.detail));
      try {
        this.users = await WA.get("/api/users");
        const stored = WA.getUserId() != null ? String(WA.getUserId()) : "";
        const ids = this.users.map((u) => String(u.id));
        if (stored && ids.includes(stored)) {
          this.currentUserId = stored;
        } else if (this.users.length) {
          this.currentUserId = String(this.users[0].id);
          WA.setUserId(this.users[0].id);
        } else {
          this.currentUserId = "";
        }
        this.$nextTick(() => this.syncSelect());
      } catch (e) { /* ignore on splash */ }
    },
    escapeHtml(s) {
      return String(s ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/"/g, "&quot;");
    },
    userOptionsHtml() {
      const rows = ['<option value="">No profile</option>'];
      for (const u of this.users) {
        const id = String(u.id);
        const label = this.escapeHtml(u.nickname || u.name || ("User " + id));
        const sel = id === String(this.currentUserId) ? " selected" : "";
        rows.push(`<option value="${id}"${sel}>${label}</option>`);
      }
      return rows.join("");
    },
    syncSelect() {
      const el = this.$refs.userSelect;
      if (el) el.value = this.currentUserId;
    },
    onUserChange(value) {
      this.currentUserId = value || "";
      WA.setUserId(this.currentUserId || null);
      location.reload();
    },
    showToast({ msg, type }) {
      this.toast = { show: true, msg, type };
      clearTimeout(this._t);
      this._t = setTimeout(() => (this.toast.show = false), 2600);
    },
    openConfirm({ title, message, confirmLabel, resolve }) {
      this.confirmDlg = {
        show: true,
        title: title || "Delete listing?",
        message: message || "This will delete the listing. This cannot be undone.",
        confirmLabel: confirmLabel || "Delete",
        resolve,
      };
    },
    closeConfirm(ok) {
      const resolve = this.confirmDlg.resolve;
      this.confirmDlg.show = false;
      this.confirmDlg.resolve = null;
      if (resolve) resolve(!!ok);
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
