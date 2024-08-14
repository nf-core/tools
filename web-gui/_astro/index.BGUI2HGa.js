function $() {}
function z(t, n) {
  for (const e in n) t[e] = n[e];
  return t;
}
function B(t) {
  return t();
}
function j() {
  return Object.create(null);
}
function y(t) {
  t.forEach(B);
}
function O(t) {
  return typeof t == "function";
}
function _t(t, n) {
  return t != t ? n == n : t !== n || (t && typeof t == "object") || typeof t == "function";
}
function F(t) {
  return Object.keys(t).length === 0;
}
function R(t, ...n) {
  if (t == null) {
    for (const i of n) i(void 0);
    return $;
  }
  const e = t.subscribe(...n);
  return e.unsubscribe ? () => e.unsubscribe() : e;
}
function ht(t, n, e) {
  t.$$.on_destroy.push(R(n, e));
}
function mt(t, n, e, i) {
  if (t) {
    const r = I(t, n, e, i);
    return t[0](r);
  }
}
function I(t, n, e, i) {
  return t[1] && i ? z(e.ctx.slice(), t[1](i(n))) : e.ctx;
}
function pt(t, n, e, i) {
  if (t[2] && i) {
    const r = t[2](i(e));
    if (n.dirty === void 0) return r;
    if (typeof r == "object") {
      const o = [],
        s = Math.max(n.dirty.length, r.length);
      for (let u = 0; u < s; u += 1) o[u] = n.dirty[u] | r[u];
      return o;
    }
    return n.dirty | r;
  }
  return n.dirty;
}
function gt(t, n, e, i, r, o) {
  if (r) {
    const s = I(n, e, i, o);
    t.p(s, r);
  }
}
function yt(t) {
  if (t.ctx.length > 32) {
    const n = [],
      e = t.ctx.length / 32;
    for (let i = 0; i < e; i++) n[i] = -1;
    return n;
  }
  return -1;
}
function xt(t) {
  return t ?? "";
}
let E = !1;
function J() {
  E = !0;
}
function K() {
  E = !1;
}
function U(t, n, e, i) {
  for (; t < n; ) {
    const r = t + ((n - t) >> 1);
    e(r) <= i ? (t = r + 1) : (n = r);
  }
  return t;
}
function V(t) {
  if (t.hydrate_init) return;
  t.hydrate_init = !0;
  let n = t.childNodes;
  if (t.nodeName === "HEAD") {
    const l = [];
    for (let c = 0; c < n.length; c++) {
      const a = n[c];
      a.claim_order !== void 0 && l.push(a);
    }
    n = l;
  }
  const e = new Int32Array(n.length + 1),
    i = new Int32Array(n.length);
  e[0] = -1;
  let r = 0;
  for (let l = 0; l < n.length; l++) {
    const c = n[l].claim_order,
      a = (r > 0 && n[e[r]].claim_order <= c ? r + 1 : U(1, r, (x) => n[e[x]].claim_order, c)) - 1;
    i[l] = e[a] + 1;
    const f = a + 1;
    (e[f] = l), (r = Math.max(f, r));
  }
  const o = [],
    s = [];
  let u = n.length - 1;
  for (let l = e[r] + 1; l != 0; l = i[l - 1]) {
    for (o.push(n[l - 1]); u >= l; u--) s.push(n[u]);
    u--;
  }
  for (; u >= 0; u--) s.push(n[u]);
  o.reverse(), s.sort((l, c) => l.claim_order - c.claim_order);
  for (let l = 0, c = 0; l < s.length; l++) {
    for (; c < o.length && s[l].claim_order >= o[c].claim_order; ) c++;
    const a = c < o.length ? o[c] : null;
    t.insertBefore(s[l], a);
  }
}
function W(t, n) {
  if (E) {
    for (
      V(t),
        (t.actual_end_child === void 0 || (t.actual_end_child !== null && t.actual_end_child.parentNode !== t)) &&
          (t.actual_end_child = t.firstChild);
      t.actual_end_child !== null && t.actual_end_child.claim_order === void 0;

    )
      t.actual_end_child = t.actual_end_child.nextSibling;
    n !== t.actual_end_child
      ? (n.claim_order !== void 0 || n.parentNode !== t) && t.insertBefore(n, t.actual_end_child)
      : (t.actual_end_child = n.nextSibling);
  } else (n.parentNode !== t || n.nextSibling !== null) && t.appendChild(n);
}
function Q(t, n, e) {
  t.insertBefore(n, e || null);
}
function X(t, n, e) {
  E && !e ? W(t, n) : (n.parentNode !== t || n.nextSibling != e) && t.insertBefore(n, e || null);
}
function w(t) {
  t.parentNode && t.parentNode.removeChild(t);
}
function k(t) {
  return document.createElement(t);
}
function Y(t) {
  return document.createElementNS("http://www.w3.org/2000/svg", t);
}
function L(t) {
  return document.createTextNode(t);
}
function bt() {
  return L(" ");
}
function $t() {
  return L("");
}
function wt(t, n, e, i) {
  return t.addEventListener(n, e, i), () => t.removeEventListener(n, e, i);
}
function Et(t, n, e) {
  e == null ? t.removeAttribute(n) : t.getAttribute(n) !== e && t.setAttribute(n, e);
}
function Nt(t) {
  return t.dataset.svelteH;
}
function Z(t) {
  return Array.from(t.childNodes);
}
function D(t) {
  t.claim_info === void 0 && (t.claim_info = { last_index: 0, total_claimed: 0 });
}
function G(t, n, e, i, r = !1) {
  D(t);
  const o = (() => {
    for (let s = t.claim_info.last_index; s < t.length; s++) {
      const u = t[s];
      if (n(u)) {
        const l = e(u);
        return l === void 0 ? t.splice(s, 1) : (t[s] = l), r || (t.claim_info.last_index = s), u;
      }
    }
    for (let s = t.claim_info.last_index - 1; s >= 0; s--) {
      const u = t[s];
      if (n(u)) {
        const l = e(u);
        return (
          l === void 0 ? t.splice(s, 1) : (t[s] = l),
          r ? l === void 0 && t.claim_info.last_index-- : (t.claim_info.last_index = s),
          u
        );
      }
    }
    return i();
  })();
  return (o.claim_order = t.claim_info.total_claimed), (t.claim_info.total_claimed += 1), o;
}
function tt(t, n, e, i) {
  return G(
    t,
    (r) => r.nodeName === n,
    (r) => {
      const o = [];
      for (let s = 0; s < r.attributes.length; s++) {
        const u = r.attributes[s];
        e[u.name] || o.push(u.name);
      }
      o.forEach((s) => r.removeAttribute(s));
    },
    () => i(n),
  );
}
function vt(t, n, e) {
  return tt(t, n, e, k);
}
function nt(t, n) {
  return G(
    t,
    (e) => e.nodeType === 3,
    (e) => {
      const i = "" + n;
      if (e.data.startsWith(i)) {
        if (e.data.length !== i.length) return e.splitText(i.length);
      } else e.data = i;
    },
    () => L(n),
    !0,
  );
}
function Tt(t) {
  return nt(t, " ");
}
function C(t, n, e) {
  for (let i = e; i < t.length; i += 1) {
    const r = t[i];
    if (r.nodeType === 8 && r.textContent.trim() === n) return i;
  }
  return -1;
}
function At(t, n) {
  const e = C(t, "HTML_TAG_START", 0),
    i = C(t, "HTML_TAG_END", e + 1);
  if (e === -1 || i === -1) return new N(n);
  D(t);
  const r = t.splice(e, i - e + 1);
  w(r[0]), w(r[r.length - 1]);
  const o = r.slice(1, r.length - 1);
  if (o.length === 0) return new N(n);
  for (const s of o) (s.claim_order = t.claim_info.total_claimed), (t.claim_info.total_claimed += 1);
  return new N(n, o);
}
function St(t, n) {
  (n = "" + n), t.data !== n && (t.data = n);
}
function Lt(t, n, e, i) {
  e == null ? t.style.removeProperty(n) : t.style.setProperty(n, e, "");
}
function Mt(t, n, e) {
  t.classList.toggle(n, !!e);
}
class et {
  is_svg = !1;
  e = void 0;
  n = void 0;
  t = void 0;
  a = void 0;
  constructor(n = !1) {
    (this.is_svg = n), (this.e = this.n = null);
  }
  c(n) {
    this.h(n);
  }
  m(n, e, i = null) {
    this.e ||
      (this.is_svg ? (this.e = Y(e.nodeName)) : (this.e = k(e.nodeType === 11 ? "TEMPLATE" : e.nodeName)),
      (this.t = e.tagName !== "TEMPLATE" ? e : e.content),
      this.c(n)),
      this.i(i);
  }
  h(n) {
    (this.e.innerHTML = n),
      (this.n = Array.from(this.e.nodeName === "TEMPLATE" ? this.e.content.childNodes : this.e.childNodes));
  }
  i(n) {
    for (let e = 0; e < this.n.length; e += 1) Q(this.t, this.n[e], n);
  }
  p(n) {
    this.d(), this.h(n), this.i(this.a);
  }
  d() {
    this.n.forEach(w);
  }
}
class N extends et {
  l = void 0;
  constructor(n = !1, e) {
    super(n), (this.e = this.n = null), (this.l = e);
  }
  c(n) {
    this.l ? (this.n = this.l) : super.c(n);
  }
  i(n) {
    for (let e = 0; e < this.n.length; e += 1) X(this.t, this.n[e], n);
  }
}
let g;
function p(t) {
  g = t;
}
function it() {
  if (!g) throw new Error("Function called outside component initialization");
  return g;
}
function Ht(t) {
  it().$$.on_mount.push(t);
}
const h = [],
  P = [];
let m = [];
const T = [],
  rt = Promise.resolve();
let A = !1;
function st() {
  A || ((A = !0), rt.then(q));
}
function S(t) {
  m.push(t);
}
function jt(t) {
  T.push(t);
}
const v = new Set();
let _ = 0;
function q() {
  if (_ !== 0) return;
  const t = g;
  do {
    try {
      for (; _ < h.length; ) {
        const n = h[_];
        _++, p(n), lt(n.$$);
      }
    } catch (n) {
      throw ((h.length = 0), (_ = 0), n);
    }
    for (p(null), h.length = 0, _ = 0; P.length; ) P.pop()();
    for (let n = 0; n < m.length; n += 1) {
      const e = m[n];
      v.has(e) || (v.add(e), e());
    }
    m.length = 0;
  } while (h.length);
  for (; T.length; ) T.pop()();
  (A = !1), v.clear(), p(t);
}
function lt(t) {
  if (t.fragment !== null) {
    t.update(), y(t.before_update);
    const n = t.dirty;
    (t.dirty = [-1]), t.fragment && t.fragment.p(t.ctx, n), t.after_update.forEach(S);
  }
}
function ct(t) {
  const n = [],
    e = [];
  m.forEach((i) => (t.indexOf(i) === -1 ? n.push(i) : e.push(i))), e.forEach((i) => i()), (m = n);
}
const b = new Set();
let d;
function Ct() {
  d = { r: 0, c: [], p: d };
}
function Pt() {
  d.r || y(d.c), (d = d.p);
}
function ot(t, n) {
  t && t.i && (b.delete(t), t.i(n));
}
function Bt(t, n, e, i) {
  if (t && t.o) {
    if (b.has(t)) return;
    b.add(t),
      d.c.push(() => {
        b.delete(t), i && (e && t.d(1), i());
      }),
      t.o(n);
  } else i && i();
}
function Ot(t, n, e) {
  const i = t.$$.props[n];
  i !== void 0 && ((t.$$.bound[i] = e), e(t.$$.ctx[i]));
}
function It(t) {
  t && t.c();
}
function kt(t, n) {
  t && t.l(n);
}
function ut(t, n, e) {
  const { fragment: i, after_update: r } = t.$$;
  i && i.m(n, e),
    S(() => {
      const o = t.$$.on_mount.map(B).filter(O);
      t.$$.on_destroy ? t.$$.on_destroy.push(...o) : y(o), (t.$$.on_mount = []);
    }),
    r.forEach(S);
}
function ft(t, n) {
  const e = t.$$;
  e.fragment !== null &&
    (ct(e.after_update),
    y(e.on_destroy),
    e.fragment && e.fragment.d(n),
    (e.on_destroy = e.fragment = null),
    (e.ctx = []));
}
function at(t, n) {
  t.$$.dirty[0] === -1 && (h.push(t), st(), t.$$.dirty.fill(0)), (t.$$.dirty[(n / 31) | 0] |= 1 << n % 31);
}
function Dt(t, n, e, i, r, o, s = null, u = [-1]) {
  const l = g;
  p(t);
  const c = (t.$$ = {
    fragment: null,
    ctx: [],
    props: o,
    update: $,
    not_equal: r,
    bound: j(),
    on_mount: [],
    on_destroy: [],
    on_disconnect: [],
    before_update: [],
    after_update: [],
    context: new Map(n.context || (l ? l.$$.context : [])),
    callbacks: j(),
    dirty: u,
    skip_bound: !1,
    root: n.target || l.$$.root,
  });
  s && s(c.root);
  let a = !1;
  if (
    ((c.ctx = e
      ? e(t, n.props || {}, (f, x, ...M) => {
          const H = M.length ? M[0] : x;
          return (
            c.ctx && r(c.ctx[f], (c.ctx[f] = H)) && (!c.skip_bound && c.bound[f] && c.bound[f](H), a && at(t, f)), x
          );
        })
      : []),
    c.update(),
    (a = !0),
    y(c.before_update),
    (c.fragment = i ? i(c.ctx) : !1),
    n.target)
  ) {
    if (n.hydrate) {
      J();
      const f = Z(n.target);
      c.fragment && c.fragment.l(f), f.forEach(w);
    } else c.fragment && c.fragment.c();
    n.intro && ot(t.$$.fragment), ut(t, n.target, n.anchor), K(), q();
  }
  p(l);
}
class Gt {
  $$ = void 0;
  $$set = void 0;
  $destroy() {
    ft(this, 1), (this.$destroy = $);
  }
  $on(n, e) {
    if (!O(e)) return $;
    const i = this.$$.callbacks[n] || (this.$$.callbacks[n] = []);
    return (
      i.push(e),
      () => {
        const r = i.indexOf(e);
        r !== -1 && i.splice(r, 1);
      }
    );
  }
  $set(n) {
    this.$$set && !F(n) && ((this.$$.skip_bound = !0), this.$$set(n), (this.$$.skip_bound = !1));
  }
}
const dt = "4";
typeof window < "u" && (window.__svelte || (window.__svelte = { v: new Set() })).v.add(dt);
export {
  Ot as A,
  $t as B,
  It as C,
  kt as D,
  ut as E,
  jt as F,
  ft as G,
  Mt as H,
  xt as I,
  N as J,
  At as K,
  Ht as L,
  $ as M,
  Lt as N,
  ht as O,
  Gt as S,
  bt as a,
  vt as b,
  mt as c,
  Z as d,
  k as e,
  Tt as f,
  Nt as g,
  w as h,
  Dt as i,
  nt as j,
  Et as k,
  X as l,
  W as m,
  wt as n,
  yt as o,
  pt as p,
  ot as q,
  Bt as r,
  _t as s,
  L as t,
  gt as u,
  y as v,
  St as w,
  Ct as x,
  Pt as y,
  P as z,
};
