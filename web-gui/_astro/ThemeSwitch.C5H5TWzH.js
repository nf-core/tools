import {
  S as gt,
  i as pt,
  s as vt,
  c as O,
  e as h,
  a as M,
  b as u,
  d as E,
  h as b,
  f as y,
  g as z,
  k as s,
  H as T,
  l as bt,
  m as o,
  n as N,
  u as F,
  o as G,
  p as J,
  q as K,
  r as Q,
  v as kt,
  L as wt,
} from "./index.BGUI2HGa.js";
/* empty css                                */ const Et = (e) => ({}),
  ut = (e) => ({}),
  Lt = (e) => ({}),
  _t = (e) => ({}),
  Ct = (e) => ({}),
  mt = (e) => ({}),
  It = (e) => ({}),
  ft = (e) => ({});
function Tt(e) {
  let n,
    l,
    k,
    D,
    v,
    $,
    d,
    L,
    P = '<span class="dropdown-header">Select theme</span>',
    q,
    w,
    a,
    R,
    S,
    at = "Light",
    W,
    C,
    c,
    X,
    A,
    nt = "Dark",
    Y,
    H,
    _,
    lt = '<i class="fa-solid fa-adjust"></i> <span class="ms-1">System</span>',
    r,
    Z,
    ot;
  const x = e[2].light,
    m = O(x, e, e[1], ft),
    tt = e[2].dark,
    f = O(tt, e, e[1], mt),
    et = e[2].light,
    g = O(et, e, e[1], _t),
    st = e[2].dark,
    p = O(st, e, e[1], ut);
  return {
    c() {
      (n = h("div")),
        (l = h("button")),
        (k = h("i")),
        m && m.c(),
        (D = M()),
        (v = h("i")),
        f && f.c(),
        ($ = M()),
        (d = h("ul")),
        (L = h("li")),
        (L.innerHTML = P),
        (q = M()),
        (w = h("li")),
        (a = h("div")),
        g && g.c(),
        (R = M()),
        (S = h("span")),
        (S.textContent = at),
        (W = M()),
        (C = h("li")),
        (c = h("div")),
        p && p.c(),
        (X = M()),
        (A = h("span")),
        (A.textContent = nt),
        (Y = M()),
        (H = h("li")),
        (_ = h("div")),
        (_.innerHTML = lt),
        this.h();
    },
    l(t) {
      n = u(t, "DIV", { class: !0, title: !0, "data-bs-toggle": !0, "data-bs-placement": !0 });
      var i = E(n);
      l = u(i, "BUTTON", { class: !0, type: !0, "data-bs-toggle": !0, "aria-expanded": !0, title: !0 });
      var U = E(l);
      k = u(U, "I", { class: !0 });
      var it = E(k);
      m && m.l(it), it.forEach(b), (D = y(U)), (v = u(U, "I", { class: !0 }));
      var rt = E(v);
      f && f.l(rt), rt.forEach(b), U.forEach(b), ($ = y(i)), (d = u(i, "UL", { class: !0 }));
      var I = E(d);
      (L = u(I, "LI", { "data-svelte-h": !0 })),
        z(L) !== "svelte-ul0184" && (L.innerHTML = P),
        (q = y(I)),
        (w = u(I, "LI", { class: !0 }));
      var dt = E(w);
      a = u(dt, "DIV", { class: !0, id: !0, title: !0, role: !0, tabindex: !0 });
      var j = E(a);
      g && g.l(j),
        (R = y(j)),
        (S = u(j, "SPAN", { class: !0, "data-svelte-h": !0 })),
        z(S) !== "svelte-ie4hvr" && (S.textContent = at),
        j.forEach(b),
        dt.forEach(b),
        (W = y(I)),
        (C = u(I, "LI", { class: !0 }));
      var ct = E(C);
      c = u(ct, "DIV", { class: !0, id: !0, title: !0, role: !0, tabindex: !0 });
      var B = E(c);
      p && p.l(B),
        (X = y(B)),
        (A = u(B, "SPAN", { class: !0, "data-svelte-h": !0 })),
        z(A) !== "svelte-w61h3n" && (A.textContent = nt),
        B.forEach(b),
        ct.forEach(b),
        (Y = y(I)),
        (H = u(I, "LI", { class: !0 }));
      var ht = E(H);
      (_ = u(ht, "DIV", { class: !0, id: !0, title: !0, role: !0, tabindex: !0, "data-svelte-h": !0 })),
        z(_) !== "svelte-hncx3b" && (_.innerHTML = lt),
        ht.forEach(b),
        I.forEach(b),
        i.forEach(b),
        this.h();
    },
    h() {
      s(k, "class", "theme-icon-light"),
        T(k, "d-none", e[0] !== "light"),
        s(v, "class", "theme-icon-dark"),
        T(v, "d-none", e[0] !== "dark"),
        s(l, "class", "nav-link dropdown-toggle"),
        s(l, "type", "button"),
        s(l, "data-bs-toggle", "dropdown"),
        s(l, "aria-expanded", "false"),
        s(l, "title", "Change theme"),
        s(S, "class", "ms-1"),
        s(a, "class", "text-decoration-none theme-option w-100 svelte-brh85i"),
        s(a, "id", "theme-light"),
        s(a, "title", "light"),
        s(a, "role", "button"),
        s(a, "tabindex", "0"),
        s(w, "class", "dropdown-item"),
        T(w, "active", e[0] === "light"),
        s(A, "class", "ms-1"),
        s(c, "class", "text-decoration-none theme-option w-100 svelte-brh85i"),
        s(c, "id", "theme-dark"),
        s(c, "title", "dark"),
        s(c, "role", "button"),
        s(c, "tabindex", "0"),
        s(C, "class", "dropdown-item"),
        T(C, "active", e[0] === "dark"),
        s(_, "class", "text-decoration-none theme-option w-100 svelte-brh85i"),
        s(_, "id", "theme-auto"),
        s(_, "title", "auto"),
        s(_, "role", "button"),
        s(_, "tabindex", "0"),
        s(H, "class", "dropdown-item"),
        s(d, "class", "dropdown-menu dropdown-menu-end"),
        s(n, "class", "dropdown"),
        s(n, "title", "Change theme"),
        s(n, "data-bs-toggle", "tooltip"),
        s(n, "data-bs-placement", "bottom");
    },
    m(t, i) {
      bt(t, n, i),
        o(n, l),
        o(l, k),
        m && m.m(k, null),
        o(l, D),
        o(l, v),
        f && f.m(v, null),
        o(n, $),
        o(n, d),
        o(d, L),
        o(d, q),
        o(d, w),
        o(w, a),
        g && g.m(a, null),
        o(a, R),
        o(a, S),
        o(d, W),
        o(d, C),
        o(C, c),
        p && p.m(c, null),
        o(c, X),
        o(c, A),
        o(d, Y),
        o(d, H),
        o(H, _),
        (r = !0),
        Z ||
          ((ot = [
            N(a, "click", e[3]),
            N(a, "keydown", e[4]),
            N(c, "click", e[5]),
            N(c, "keydown", e[6]),
            N(_, "click", e[7]),
            N(_, "keydown", e[8]),
          ]),
          (Z = !0));
    },
    p(t, [i]) {
      m && m.p && (!r || i & 2) && F(m, x, t, t[1], r ? J(x, t[1], i, It) : G(t[1]), ft),
        (!r || i & 1) && T(k, "d-none", t[0] !== "light"),
        f && f.p && (!r || i & 2) && F(f, tt, t, t[1], r ? J(tt, t[1], i, Ct) : G(t[1]), mt),
        (!r || i & 1) && T(v, "d-none", t[0] !== "dark"),
        g && g.p && (!r || i & 2) && F(g, et, t, t[1], r ? J(et, t[1], i, Lt) : G(t[1]), _t),
        (!r || i & 1) && T(w, "active", t[0] === "light"),
        p && p.p && (!r || i & 2) && F(p, st, t, t[1], r ? J(st, t[1], i, Et) : G(t[1]), ut),
        (!r || i & 1) && T(C, "active", t[0] === "dark");
    },
    i(t) {
      r || (K(m, t), K(f, t), K(g, t), K(p, t), (r = !0));
    },
    o(t) {
      Q(m, t), Q(f, t), Q(g, t), Q(p, t), (r = !1);
    },
    d(t) {
      t && b(n), m && m.d(t), f && f.d(t), g && g.d(t), p && p.d(t), (Z = !1), kt(ot);
    },
  };
}
function St(e) {
  const n = document.documentElement;
  e === "auto"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
      ? n.setAttribute("data-bs-theme", "dark")
      : n.setAttribute("data-bs-theme", "light")
    : n.setAttribute("data-bs-theme", e);
}
function V(e) {
  const n = e.target;
  let l = "";
  n.tagName !== "div" || !n.title ? (l = n.closest("div.theme-option").title) : (l = e.target.title),
    localStorage.setItem("theme", l),
    St(l),
    window.dispatchEvent(new Event("theme-changed"));
}
function At(e, n, l) {
  let { $$slots: k = {}, $$scope: D } = n,
    v = "dark";
  wt(() => {
    l(0, (v = document.documentElement.getAttribute("data-bs-theme") || "auto")),
      window.addEventListener("theme-changed", (a) => {
        l(0, (v = document.documentElement.getAttribute("data-bs-theme")));
      });
  });
  const $ = (a) => V(a),
    d = (a) => V(a),
    L = (a) => V(a),
    P = (a) => V(a),
    q = (a) => V(a),
    w = (a) => V(a);
  return (
    (e.$$set = (a) => {
      "$$scope" in a && l(1, (D = a.$$scope));
    }),
    [v, D, k, $, d, L, P, q, w]
  );
}
class Dt extends gt {
  constructor(n) {
    super(), pt(this, n, At, Tt, vt, {});
  }
}
export { Dt as default };
