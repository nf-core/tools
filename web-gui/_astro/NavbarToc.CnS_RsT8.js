import {
  S as ee,
  i as te,
  s as ne,
  e as b,
  t as S,
  a as I,
  b as E,
  d as k,
  j as O,
  h as m,
  f as x,
  k as f,
  l as D,
  m as p,
  n as q,
  w as Q,
  M as P,
  v as se,
  O as A,
  g as ie,
  q as B,
  r as C,
  y as ae,
  J as re,
  K as oe,
  H as G,
  C as de,
  D as ue,
  E as ce,
  G as fe,
  x as he,
  I as Y,
} from "./index.BGUI2HGa.js";
import { e as z, u as _e, d as ve } from "./each.gC3iQszE.js";
/* empty css                                */ let w = [],
  y = 0;
const N = 4;
let R = (n) => {
  let t = [],
    e = {
      get() {
        return e.lc || e.listen(() => {})(), e.value;
      },
      lc: 0,
      listen(l) {
        return (
          (e.lc = t.push(l)),
          () => {
            for (let a = y + N; a < w.length; ) w[a] === l ? w.splice(a, N) : (a += N);
            let s = t.indexOf(l);
            ~s && (t.splice(s, 1), --e.lc || e.off());
          }
        );
      },
      notify(l, s) {
        let a = !w.length;
        for (let i of t) w.push(i, e.value, l, s);
        if (a) {
          for (y = 0; y < w.length; y += N) w[y](w[y + 1], w[y + 2], w[y + 3]);
          w.length = 0;
        }
      },
      off() {},
      set(l) {
        let s = e.value;
        s !== l && ((e.value = l), e.notify(s));
      },
      subscribe(l) {
        let s = e.listen(l);
        return l(e.value), s;
      },
      value: n,
    };
  return e;
};
const pe = 5,
  M = 6,
  U = 10;
let ge = (n, t, e, l) => (
    (n.events = n.events || {}),
    n.events[e + U] ||
      (n.events[e + U] = l((s) => {
        n.events[e].reduceRight((a, i) => (i(a), a), { shared: {}, ...s });
      })),
    (n.events[e] = n.events[e] || []),
    n.events[e].push(t),
    () => {
      let s = n.events[e],
        a = s.indexOf(t);
      s.splice(a, 1), s.length || (delete n.events[e], n.events[e + U](), delete n.events[e + U]);
    }
  ),
  me = 1e3,
  we = (n, t) =>
    ge(
      n,
      (l) => {
        let s = t(l);
        s && n.events[M].push(s);
      },
      pe,
      (l) => {
        let s = n.listen;
        n.listen = (...i) => (!n.lc && !n.active && ((n.active = !0), l()), s(...i));
        let a = n.off;
        return (
          (n.events[M] = []),
          (n.off = () => {
            a(),
              setTimeout(() => {
                if (n.active && !n.lc) {
                  n.active = !1;
                  for (let i of n.events[M]) i();
                  n.events[M] = [];
                }
              }, me);
          }),
          () => {
            (n.listen = s), (n.off = a);
          }
        );
      },
    ),
  F = (n) => n,
  T = {},
  V = { addEventListener() {}, removeEventListener() {} };
function be() {
  try {
    return typeof localStorage < "u";
  } catch {
    return !1;
  }
}
be() && (T = localStorage);
let Ee = {
  addEventListener(n, t, e) {
    window.addEventListener("storage", t), window.addEventListener("pageshow", e);
  },
  removeEventListener(n, t, e) {
    window.removeEventListener("storage", t), window.removeEventListener("pageshow", e);
  },
};
typeof window < "u" && (V = Ee);
function le(n, t = void 0, e = {}) {
  let l = e.encode || F,
    s = e.decode || F,
    a = R(t),
    i = a.set;
  a.set = (c) => {
    typeof c > "u" ? delete T[n] : (T[n] = l(c)), i(c);
  };
  function r(c) {
    c.key === n ? (c.newValue === null ? i(void 0) : i(s(c.newValue))) : T[n] || i(void 0);
  }
  function d() {
    a.set(T[n] ? s(T[n]) : t);
  }
  return (
    we(a, () => {
      if ((d(), e.listen !== !1))
        return (
          V.addEventListener(n, r, d),
          () => {
            V.removeEventListener(n, r, d);
          }
        );
    }),
    a
  );
}
le("DisplayStyle", "grid", {
  encode(n) {
    return JSON.stringify(n);
  },
  decode(n) {
    return JSON.parse(n);
  },
});
le("Checkboxes", [], {
  encode(n) {
    return JSON.stringify(n);
  },
  decode(n) {
    return JSON.parse(n);
  },
});
const ke = R(""),
  W = R(!1),
  X = R(!1);
function ye(n) {
  let t,
    e,
    l = n[0] ? "Hide" : "Show",
    s,
    a,
    i,
    r,
    d = n[1] ? "Hide" : "Show",
    c,
    _,
    g,
    H;
  return {
    c() {
      (t = b("div")),
        (e = b("button")),
        (s = S(l)),
        (a = S(" hidden")),
        (i = I()),
        (r = b("button")),
        (c = S(d)),
        (_ = S(" all help texts")),
        this.h();
    },
    l(u) {
      t = E(u, "DIV", { class: !0, role: !0, "aria-label": !0 });
      var o = k(t);
      e = E(o, "BUTTON", { type: !0, class: !0 });
      var h = k(e);
      (s = O(h, l)), (a = O(h, " hidden")), h.forEach(m), (i = x(o)), (r = E(o, "BUTTON", { type: !0, class: !0 }));
      var v = k(r);
      (c = O(v, d)), (_ = O(v, " all help texts")), v.forEach(m), o.forEach(m), this.h();
    },
    h() {
      f(e, "type", "button"),
        f(e, "class", "btn btn-outline-secondary btn-sm"),
        f(r, "type", "button"),
        f(r, "class", "btn btn-outline-secondary btn-sm"),
        f(t, "class", "btn-group btn-sm w-100 px-3 px-xl-0"),
        f(t, "role", "group"),
        f(t, "aria-label", "Show/Hide hidden parameters and help texts");
    },
    m(u, o) {
      D(u, t, o),
        p(t, e),
        p(e, s),
        p(e, a),
        p(t, i),
        p(t, r),
        p(r, c),
        p(r, _),
        g || ((H = [q(e, "click", n[2]), q(r, "click", n[3])]), (g = !0));
    },
    p(u, [o]) {
      o & 1 && l !== (l = u[0] ? "Hide" : "Show") && Q(s, l), o & 2 && d !== (d = u[1] ? "Hide" : "Show") && Q(c, d);
    },
    i: P,
    o: P,
    d(u) {
      u && m(t), (g = !1), se(H);
    },
  };
}
function Te(n, t, e) {
  let l, s;
  return A(n, W, (r) => e(0, (l = r))), A(n, X, (r) => e(1, (s = r))), [l, s, () => W.set(!l), () => X.set(!s)];
}
class He extends ee {
  constructor(t) {
    super(), te(this, t, Te, ye, ne, {});
  }
}
function Z(n, t, e) {
  const l = n.slice();
  return (l[3] = t[e]), l;
}
function K(n) {
  let t, e;
  return {
    c() {
      (t = b("i")), this.h();
    },
    l(l) {
      (t = E(l, "I", { class: !0, "aria-hidden": !0 })), k(t).forEach(m), this.h();
    },
    h() {
      f(t, "class", (e = Y(n[3].fa_icon) + " svelte-15vokto")), f(t, "aria-hidden", "true");
    },
    m(l, s) {
      D(l, t, s);
    },
    p(l, s) {
      s & 1 && e !== (e = Y(l[3].fa_icon) + " svelte-15vokto") && f(t, "class", e);
    },
    d(l) {
      l && m(t);
    },
  };
}
function j(n, t) {
  let e,
    l,
    s,
    a,
    i = t[3].text + "",
    r,
    d = t[3].fa_icon && K(t);
  return {
    key: n,
    first: null,
    c() {
      (e = b("li")), (l = b("a")), d && d.c(), (s = I()), (a = new re(!1)), this.h();
    },
    l(c) {
      e = E(c, "LI", { class: !0 });
      var _ = k(e);
      l = E(_, "A", { class: !0, href: !0 });
      var g = k(l);
      d && d.l(g), (s = x(g)), (a = oe(g, !1)), g.forEach(m), _.forEach(m), this.h();
    },
    h() {
      (a.a = null),
        f(l, "class", "dropdown-item"),
        f(l, "href", (r = "#" + t[3].slug)),
        f(e, "class", "svelte-15vokto"),
        G(e, "active", t[3].slug === t[2]),
        (this.first = e);
    },
    m(c, _) {
      D(c, e, _), p(e, l), d && d.m(l, null), p(l, s), a.m(i, l);
    },
    p(c, _) {
      (t = c),
        t[3].fa_icon ? (d ? d.p(t, _) : ((d = K(t)), d.c(), d.m(l, s))) : d && (d.d(1), (d = null)),
        _ & 1 && i !== (i = t[3].text + "") && a.p(i),
        _ & 1 && r !== (r = "#" + t[3].slug) && f(l, "href", r),
        _ & 5 && G(e, "active", t[3].slug === t[2]);
    },
    d(c) {
      c && m(e), d && d.d();
    },
  };
}
function $(n) {
  let t, e;
  return (
    (t = new He({})),
    {
      c() {
        de(t.$$.fragment);
      },
      l(l) {
        ue(t.$$.fragment, l);
      },
      m(l, s) {
        ce(t, l, s), (e = !0);
      },
      i(l) {
        e || (B(t.$$.fragment, l), (e = !0));
      },
      o(l) {
        C(t.$$.fragment, l), (e = !1);
      },
      d(l) {
        fe(t, l);
      },
    }
  );
}
function Le(n) {
  let t,
    e,
    l,
    s = '<i class="fa-solid fa-list" aria-hidden="true"></i> On this page',
    a,
    i,
    r = [],
    d = new Map(),
    c,
    _,
    g = z(n[0]);
  const H = (o) => o[3];
  for (let o = 0; o < g.length; o += 1) {
    let h = Z(n, g, o),
      v = H(h);
    d.set(v, (r[o] = j(v, h)));
  }
  let u = n[1] && $();
  return {
    c() {
      (t = b("div")), (e = b("div")), (l = b("button")), (l.innerHTML = s), (a = I()), (i = b("ul"));
      for (let o = 0; o < r.length; o += 1) r[o].c();
      (c = I()), u && u.c(), this.h();
    },
    l(o) {
      t = E(o, "DIV", { class: !0 });
      var h = k(t);
      e = E(h, "DIV", { class: !0 });
      var v = k(e);
      (l = E(v, "BUTTON", {
        class: !0,
        type: !0,
        id: !0,
        "data-bs-toggle": !0,
        "aria-expanded": !0,
        "data-svelte-h": !0,
      })),
        ie(l) !== "svelte-1d1rnsn" && (l.innerHTML = s),
        (a = x(v)),
        (i = E(v, "UL", { class: !0, "aria-labelledby": !0 }));
      var L = k(i);
      for (let J = 0; J < r.length; J += 1) r[J].l(L);
      (c = x(L)), u && u.l(L), L.forEach(m), v.forEach(m), h.forEach(m), this.h();
    },
    h() {
      f(l, "class", "btn btn-sm btn-outline-secondary dropdown-toggle text-body-secondary"),
        f(l, "type", "button"),
        f(l, "id", "dropdownMenuButton"),
        f(l, "data-bs-toggle", "dropdown"),
        f(l, "aria-expanded", "false"),
        f(i, "class", "dropdown-menu svelte-15vokto"),
        f(i, "aria-labelledby", "dropdownMenuButton"),
        f(e, "class", "dropdown"),
        f(t, "class", "d-md-none toc-md svelte-15vokto");
    },
    m(o, h) {
      D(o, t, h), p(t, e), p(e, l), p(e, a), p(e, i);
      for (let v = 0; v < r.length; v += 1) r[v] && r[v].m(i, null);
      p(i, c), u && u.m(i, null), (_ = !0);
    },
    p(o, [h]) {
      h & 5 && ((g = z(o[0])), (r = _e(r, h, H, 1, o, g, d, i, ve, j, c, Z))),
        o[1]
          ? u
            ? h & 2 && B(u, 1)
            : ((u = $()), u.c(), B(u, 1), u.m(i, null))
          : u &&
            (he(),
            C(u, 1, 1, () => {
              u = null;
            }),
            ae());
    },
    i(o) {
      _ || (B(u), (_ = !0));
    },
    o(o) {
      C(u), (_ = !1);
    },
    d(o) {
      o && m(t);
      for (let h = 0; h < r.length; h += 1) r[h].d();
      u && u.d();
    },
  };
}
function Se(n, t, e) {
  let l;
  A(n, ke, (i) => e(2, (l = i)));
  let { headings: s } = t,
    { showHiddenBtn: a } = t;
  return (
    (n.$$set = (i) => {
      "headings" in i && e(0, (s = i.headings)), "showHiddenBtn" in i && e(1, (a = i.showHiddenBtn));
    }),
    [s, a, l]
  );
}
class Ue extends ee {
  constructor(t) {
    super(), te(this, t, Se, Le, ne, { headings: 0, showHiddenBtn: 1 });
  }
}
export { Ue as default };
