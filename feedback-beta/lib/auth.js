const crypto = require("crypto");
const { redis, parseCookies, SESSION_COOKIE } = require("./http");

function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return { salt, hash };
}

function verifyPassword(password, salt, hash) {
  try {
    const next = crypto.scryptSync(password, salt, 64).toString("hex");
    const a = Buffer.from(hash, "hex");
    const b = Buffer.from(next, "hex");
    if (a.length !== b.length) return false;
    return crypto.timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

function newToken() {
  return crypto.randomBytes(32).toString("hex");
}

function normalizeUsername(username) {
  return String(username || "")
    .trim()
    .toLowerCase();
}

function isValidUsername(username) {
  return /^[a-z0-9_]{3,32}$/.test(username);
}

async function createUser({ name, username, password }) {
  const r = redis();
  const normalized = normalizeUsername(username);
  if (!isValidUsername(normalized)) {
    const err = new Error("username: 3–32 chars, letters/numbers/_ only");
    err.status = 400;
    throw err;
  }
  const existing = await r.get(`user:username:${normalized}`);
  if (existing) {
    const err = new Error("username already taken");
    err.status = 409;
    throw err;
  }
  const id = crypto.randomUUID();
  const { salt, hash } = hashPassword(password);
  const display = (name || "").trim() || normalized;
  const now = new Date().toISOString();
  const user = {
    id,
    name: display,
    username: normalized,
    salt,
    password_hash: hash,
    created_at: now,
    last_login_at: now,
    login_count: 1,
    role: "reader",
  };
  await r.set(`user:${id}`, user);
  await r.set(`user:username:${normalized}`, id);
  await r.sadd("users", id);
  await pushLoginEvent(r, { action: "register", user_id: id, username: normalized, name: display, at: now });
  return publicUser(user);
}

async function pushLoginEvent(r, event) {
  try {
    await r.lpush("login_events", event);
    await r.ltrim("login_events", 0, 499);
  } catch {
    /* ignore analytics failures */
  }
}

async function loginUser({ username, password }) {
  const r = redis();
  const normalized = normalizeUsername(username);
  const id = await r.get(`user:username:${normalized}`);
  if (!id) {
    const err = new Error("invalid username or password");
    err.status = 401;
    throw err;
  }
  const user = await r.get(`user:${id}`);
  if (!user || !verifyPassword(password, user.salt, user.password_hash)) {
    const err = new Error("invalid username or password");
    err.status = 401;
    throw err;
  }
  const now = new Date().toISOString();
  user.last_login_at = now;
  user.login_count = Number(user.login_count || 0) + 1;
  await r.set(`user:${id}`, user);
  await pushLoginEvent(r, {
    action: "login",
    user_id: user.id,
    username: user.username,
    name: user.name,
    at: now,
  });
  const token = newToken();
  const session = {
    token,
    user_id: user.id,
    created_at: now,
  };
  await r.set(`session:${token}`, session, { ex: 60 * 60 * 24 * 30 }); // 30d
  return { token, user: publicUser(user) };
}

function tokenFromRequest(req) {
  const header = req.headers.authorization || "";
  if (header.startsWith("Bearer ")) return header.slice(7).trim();
  const xt = req.headers["x-session-token"];
  if (xt) return String(xt).trim();
  const cookies = parseCookies(req);
  return (cookies[SESSION_COOKIE] || "").trim();
}

async function userFromAuthHeader(req) {
  const token = tokenFromRequest(req);
  if (!token) return null;
  const r = redis();
  const session = await r.get(`session:${token}`);
  if (!session) return null;
  const userId = session.user_id || session.userId;
  if (!userId) return null;
  const user = await r.get(`user:${userId}`);
  return user ? publicUser(user) : null;
}

function publicUser(user) {
  return {
    id: user.id,
    name: user.name,
    username: user.username,
    created_at: user.created_at,
    last_login_at: user.last_login_at || null,
    login_count: user.login_count || 0,
    role: user.role || "reader",
  };
}

async function requireUser(req) {
  const user = await userFromAuthHeader(req);
  if (!user) {
    const err = new Error("login required");
    err.status = 401;
    throw err;
  }
  return user;
}

async function destroySession(req) {
  const token = tokenFromRequest(req);
  if (token) {
    try {
      await redis().del(`session:${token}`);
    } catch {
      /* ignore */
    }
  }
  return token;
}

module.exports = {
  createUser,
  loginUser,
  userFromAuthHeader,
  requireUser,
  publicUser,
  destroySession,
  tokenFromRequest,
};
