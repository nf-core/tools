import {
  S as U,
  i as j,
  s as F,
  c as z,
  e as h,
  a as w,
  B as q,
  b as g,
  d as y,
  h as m,
  f as D,
  k as v,
  l as $,
  m as k,
  n as I,
  u as C,
  o as O,
  p as P,
  q as E,
  r as V,
  y as G,
  v as H,
  x as J,
} from "./index.BGUI2HGa.js";
/* empty css                                */ const K = (l) => ({}),
  A = (l) => ({}),
  L = (l) => ({}),
  B = (l) => ({});
function T(l) {
  let t, a, r, f, c, p, _;
  const b = l[3].menu,
    i = z(b, l, l[2], A);
  return {
    c() {
      (t = h("div")), (a = h("span")), (r = w()), (f = h("nav")), i && i.c(), this.h();
    },
    l(o) {
      t = g(o, "DIV", { class: !0 });
      var u = y(t);
      (a = g(u, "SPAN", { class: !0, role: !0, tabindex: !0 })),
        y(a).forEach(m),
        (r = D(u)),
        (f = g(u, "NAV", { class: !0 }));
      var n = y(f);
      i && i.l(n), n.forEach(m), u.forEach(m), this.h();
    },
    h() {
      v(a, "class", "position-fixed bg-dark bg-opacity-75 w-100 min-vh-100"),
        v(a, "role", "button"),
        v(a, "tabindex", "0"),
        v(f, "class", "side-nav bg-body pb-2 px-0 text-gray-400 overflow-y-auto svelte-169mbi2"),
        v(t, "class", "d-md-none bg-body z-3");
    },
    m(o, u) {
      $(o, t, u),
        k(t, a),
        k(t, r),
        k(t, f),
        i && i.m(f, null),
        (c = !0),
        p || ((_ = [I(a, "click", l[1]), I(a, "keypress", l[1])]), (p = !0));
    },
    p(o, u) {
      i && i.p && (!c || u & 4) && C(i, b, o, o[2], c ? P(b, o[2], u, K) : O(o[2]), A);
    },
    i(o) {
      c || (E(i, o), (c = !0));
    },
    o(o) {
      V(i, o), (c = !1);
    },
    d(o) {
      o && m(t), i && i.d(o), (p = !1), H(_);
    },
  };
}
function M(l) {
  let t, a, r, f, c, p, _, b, i, o;
  const u = l[3].title,
    n = z(u, l, l[2], B);
  let s = l[0] && T(l);
  return {
    c() {
      (t = h("div")),
        (a = h("div")),
        (r = h("button")),
        (f = h("i")),
        (c = w()),
        n && n.c(),
        (p = w()),
        s && s.c(),
        (_ = q()),
        this.h();
    },
    l(e) {
      t = g(e, "DIV", { class: !0 });
      var d = y(t);
      a = g(d, "DIV", { class: !0 });
      var S = y(a);
      r = g(S, "BUTTON", { class: !0 });
      var N = y(r);
      (f = g(N, "I", { class: !0 })),
        y(f).forEach(m),
        (c = D(N)),
        n && n.l(N),
        N.forEach(m),
        S.forEach(m),
        d.forEach(m),
        (p = D(e)),
        s && s.l(e),
        (_ = q()),
        this.h();
    },
    h() {
      v(f, "class", "fa-regular fa-ellipsis-vertical me-2"),
        v(r, "class", "btn text-body d-flex align-items-center ps-2"),
        v(a, "class", "w-100 text-nowrap"),
        v(t, "class", "docs-nav fixed-top bg-body small border-bottom d-md-none svelte-169mbi2");
    },
    m(e, d) {
      $(e, t, d),
        k(t, a),
        k(a, r),
        k(r, f),
        k(r, c),
        n && n.m(r, null),
        $(e, p, d),
        s && s.m(e, d),
        $(e, _, d),
        (b = !0),
        i || ((o = I(r, "click", l[1])), (i = !0));
    },
    p(e, [d]) {
      n && n.p && (!b || d & 4) && C(n, u, e, e[2], b ? P(u, e[2], d, L) : O(e[2]), B),
        e[0]
          ? s
            ? (s.p(e, d), d & 1 && E(s, 1))
            : ((s = T(e)), s.c(), E(s, 1), s.m(_.parentNode, _))
          : s &&
            (J(),
            V(s, 1, 1, () => {
              s = null;
            }),
            G());
    },
    i(e) {
      b || (E(n, e), E(s), (b = !0));
    },
    o(e) {
      V(n, e), V(s), (b = !1);
    },
    d(e) {
      e && (m(t), m(p), m(_)), n && n.d(e), s && s.d(e), (i = !1), o();
    },
  };
}
function Q(l, t, a) {
  let { $$slots: r = {}, $$scope: f } = t,
    c = !1;
  function p() {
    a(0, (c = !c));
  }
  return (
    (l.$$set = (_) => {
      "$$scope" in _ && a(2, (f = _.$$scope));
    }),
    [c, p, f, r]
  );
}
class X extends U {
  constructor(t) {
    super(), j(this, t, Q, M, F, {});
  }
}
export { X as default };
