import { v as A, q as j, r as z } from "./index.BGUI2HGa.js";
function D(n) {
  return n?.length !== void 0 ? n : Array.from(n);
}
function E(n, d) {
  n.d(1), d.delete(n.key);
}
function F(n, d) {
  z(n, 1, 1, () => {
    d.delete(n.key);
  });
}
function G(n, d, v, B, M, r, o, S, m, q, h, x) {
  let i = n.length,
    c = r.length,
    a = i;
  const w = {};
  for (; a--; ) w[n[a].key] = a;
  const l = [],
    u = new Map(),
    y = new Map(),
    g = [];
  for (a = c; a--; ) {
    const e = x(M, r, a),
      t = v(e);
    let s = o.get(t);
    s ? g.push(() => s.p(e, d)) : ((s = q(t, e)), s.c()), u.set(t, (l[a] = s)), t in w && y.set(t, Math.abs(a - w[t]));
  }
  const k = new Set(),
    p = new Set();
  function _(e) {
    j(e, 1), e.m(S, h), o.set(e.key, e), (h = e.first), c--;
  }
  for (; i && c; ) {
    const e = l[c - 1],
      t = n[i - 1],
      s = e.key,
      f = t.key;
    e === t
      ? ((h = e.first), i--, c--)
      : u.has(f)
        ? !o.has(s) || k.has(s)
          ? _(e)
          : p.has(f)
            ? i--
            : y.get(s) > y.get(f)
              ? (p.add(s), _(e))
              : (k.add(f), i--)
        : (m(t, o), i--);
  }
  for (; i--; ) {
    const e = n[i];
    u.has(e.key) || m(e, o);
  }
  for (; c; ) _(l[c - 1]);
  return A(g), l;
}
export { E as d, D as e, F as o, G as u };
