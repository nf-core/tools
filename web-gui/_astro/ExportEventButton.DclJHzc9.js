import {
  S as X,
  i as z,
  s as J,
  e as U,
  t as F,
  a as B,
  b as w,
  d as S,
  h as R,
  j as H,
  f as k,
  g as $,
  k as f,
  l as tt,
  m as D,
  n as et,
  M as Q,
} from "./index.BGUI2HGa.js";
import { c as C, a as at } from "./_commonjsHelpers.C4iS2aBk.js";
var rt = { FREQUENCY: { DAILY: "DAILY", WEEKLY: "WEEKLY", MONTHLY: "MONTHLY", YEARLY: "YEARLY" } },
  T = {
    DATE: "YYYYMMDD",
    TIME: "ThhmmssZ",
    FULL: "YYYYMMDDThhmmssZ",
    NO_UTC_FULL: "YYYYMMDDThhmmss",
    OUTLOOK_DATE: "YYYY-MM-DD",
    OUTLOOK_TIME: "Thh:mm:ssZ",
    OUTLOOK_FULL: "YYYY-MM-DDThh:mm:ssZ",
  },
  I = {
    YAHOO: "https://calendar.yahoo.com/",
    GOOGLE: "https://calendar.google.com/calendar/render",
    OUTLOOK: "https://outlook.{{host}}.com/calendar/0/deeplink/compose",
  },
  E = function (a) {
    return a === void 0 && (a = ""), "0".concat(parseInt(a.toString(), 10)).slice(-2);
  },
  nt = function (a, n) {
    var r = Math.floor((n - a) / 1e3),
      t = Math.floor(r / 3600),
      e = ((r / 3600) % 1) * 60;
    return "".concat(E(t)).concat(E(e));
  },
  ot = function (a, n) {
    var r = Math.floor((n - a) / 1e3);
    return Math.floor(r / 3600);
  },
  it = function (a) {
    var n = a.frequency,
      r = a.interval,
      t = rt.FREQUENCY;
    if (r)
      switch (n) {
        case t.YEARLY:
          return r * 365.25;
        case t.MONTHLY:
          return r * 30.42;
        case t.WEEKLY:
          return r * 7;
        default:
          return r;
      }
    return 365.25 * 100;
  },
  Z = function (a, n) {
    a === void 0 && (a = new Date());
    var r = {
      YYYY: a.getUTCFullYear(),
      MM: E(a.getUTCMonth() + 1),
      DD: E(a.getUTCDate()),
      hh: E(a.getUTCHours()),
      mm: E(a.getUTCMinutes()),
      ss: E(a.getUTCSeconds()),
    };
    return Object.keys(r).reduce(function (t, e) {
      return t.replace(e, r[e].toString());
    }, n);
  },
  st = function (a, n) {
    a === void 0 && (a = new Date());
    var r = {
      YYYY: a.getFullYear(),
      MM: E(a.getMonth() + 1),
      DD: E(a.getDate()),
      hh: E(a.getHours()),
      mm: E(a.getMinutes()),
      ss: E(a.getSeconds()),
    };
    return Object.keys(r).reduce(function (t, e) {
      return t.replace(e, r[e].toString());
    }, n);
  },
  ct = function () {
    return Z(new Date(), T.FULL);
  },
  lt = function (a, n) {
    var r = n * 864e5,
      t = new Date();
    return t.setTime(a.getTime() + r), t;
  },
  v = {
    addLeadingZero: E,
    getDuration: nt,
    getHoursDiff: ot,
    getRecurrenceLengthDays: it,
    formatDate: Z,
    formatDateNoUtc: st,
    getTimeCreated: ct,
    incrementDate: lt,
  },
  N = (function () {
    function a(n) {
      var r = this;
      (this.isAllDay = !1),
        (this.description = ""),
        (this.title = ""),
        (this.location = ""),
        (this.start = new Date()),
        (this.end = new Date()),
        (this.params = {}),
        (this.attendees = []),
        (this.setText = function (t) {
          (r.description = t.description || ""), (r.title = t.title || ""), (r.location = t.location || "");
        }),
        (this.setTimestamps = function (t) {
          (r.isAllDay = !t.end),
            (r.start = t.start),
            (r.end = t.end || v.incrementDate(r.start, 1)),
            (r.recurrence = t.recurrence);
        }),
        (this.setParam = function (t, e) {
          return (r.params[t] = e), r;
        }),
        this.setText(n),
        this.setTimestamps(n),
        this.setAttendees(n);
    }
    return (
      (a.prototype.setAttendees = function (n) {
        this.attendees = Array.isArray(n.attendees) ? n.attendees : [];
      }),
      a
    );
  })(),
  G = function (a, n) {
    return (
      (G =
        Object.setPrototypeOf ||
        ({ __proto__: [] } instanceof Array &&
          function (r, t) {
            r.__proto__ = t;
          }) ||
        function (r, t) {
          for (var e in t) Object.prototype.hasOwnProperty.call(t, e) && (r[e] = t[e]);
        }),
      G(a, n)
    );
  };
function j(a, n) {
  if (typeof n != "function" && n !== null)
    throw new TypeError("Class extends value " + String(n) + " is not a constructor or null");
  G(a, n);
  function r() {
    this.constructor = a;
  }
  a.prototype = n === null ? Object.create(n) : ((r.prototype = n.prototype), new r());
}
var b = function () {
  return (
    (b =
      Object.assign ||
      function (n) {
        for (var r, t = 1, e = arguments.length; t < e; t++) {
          r = arguments[t];
          for (var o in r) Object.prototype.hasOwnProperty.call(r, o) && (n[o] = r[o]);
        }
        return n;
      }),
    b.apply(this, arguments)
  );
};
function L(a, n, r) {
  if (r || arguments.length === 2)
    for (var t = 0, e = n.length, o; t < e; t++)
      (o || !(t in n)) && (o || (o = Array.prototype.slice.call(n, 0, t)), (o[t] = n[t]));
  return a.concat(o || Array.prototype.slice.call(n));
}
var V = function (a, n, r) {
    n === void 0 && (n = ";"),
      r === void 0 &&
        (r = function (o) {
          return o;
        });
    var t = [];
    for (var e in a) a.hasOwnProperty(e) && a[e] !== void 0 && t.push("".concat(e, "=").concat(r(a[e])));
    return t.join(n);
  },
  ut = function (a) {
    var n = Object.keys(a)
      .filter(function (r) {
        return a[r] !== null;
      })
      .reduce(function (r, t) {
        var e;
        return b(b({}, r), ((e = {}), (e[t] = a[t]), e));
      }, {});
    return V(n, "&", encodeURIComponent);
  },
  dt = function (a) {
    return V(a, ";");
  },
  ft = function (a) {
    return a.map(function (n) {
      var r = n.email,
        t = n.name;
      return t ? "".concat(t, " <").concat(r, ">") : r;
    });
  },
  mt = function (a) {
    return [a[0].toUpperCase(), a.slice(-a.length + 1).toLowerCase()].join("");
  },
  P = { toParamString: V, toQueryString: ut, toIcsParamString: dt, toMailtoList: ft, toProperCase: mt },
  vt = function (a) {
    return a === void 0 && (a = ""), a.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/[,;]/g, "\\$&");
  },
  pt = function () {
    return Math.random().toString(36).substr(2);
  },
  gt = function () {
    return typeof window < "u" ? window.location.host : "datebook";
  },
  ht = function (a) {
    var n,
      r,
      t = {
        FREQ: a.frequency,
        INTERVAL: (n = a.interval) === null || n === void 0 ? void 0 : n.toString(),
        COUNT: (r = a.count) === null || r === void 0 ? void 0 : r.toString(),
        WKST: a.weekstart,
        BYDAY: a.weekdays,
        BYMONTHDAY: a.monthdays,
      };
    return a.end && (t.UNTIL = v.formatDate(a.end, T.FULL)), P.toIcsParamString(t);
  },
  y = { formatText: vt, getUid: pt, getProdId: gt, getRrule: ht },
  Tt = (function (a) {
    j(n, a);
    function n(r) {
      var t = a.call(this, r) || this;
      return (
        (t.setInitialParams = function () {
          var e = T.DATE;
          t.isAllDay || (e += T.TIME);
          var o = [v.formatDate(t.start, e), v.formatDate(t.end, e)].join("/");
          t
            .setParam("action", "TEMPLATE")
            .setParam("dates", o)
            .setParam("text", t.title)
            .setParam("details", t.description)
            .setParam("location", t.location)
            .setParam("allday", t.isAllDay.toString()),
            t.recurrence && t.setParam("recur", "RRULE:".concat(y.getRrule(t.recurrence))),
            t.attendees.length > 0 && t.setParam("add", P.toMailtoList(t.attendees).join(","));
        }),
        (t.render = function () {
          var e = I.GOOGLE,
            o = P.toQueryString(t.params);
          return "".concat(e, "?").concat(o);
        }),
        t.setInitialParams(),
        t
      );
    }
    return n;
  })(N);
(function (a) {
  j(n, a);
  function n(r) {
    var t = a.call(this, r) || this;
    return (
      (t.setInitialParams = function () {
        t.setParam("v", "60").setParam("title", t.title).setParam("desc", t.description).setParam("in_loc", t.location),
          t.setTimeParams(),
          t.attendees.length > 0 && t.setParam("inv_list", P.toMailtoList(t.attendees).join(","));
      }),
      (t.setTimeParams = function () {
        t.isAllDay
          ? t.setParam("dur", "allday").setParam("st", v.formatDateNoUtc(t.start, T.DATE))
          : (t.setParam("st", v.formatDateNoUtc(t.start, T.NO_UTC_FULL)),
            v.getHoursDiff(t.start.getTime(), t.end.getTime()) > 99
              ? t.setParam("et", v.formatDateNoUtc(t.end, T.NO_UTC_FULL))
              : t.setParam("dur", v.getDuration(t.start.getTime(), t.end.getTime())));
      }),
      (t.render = function () {
        var e = I.YAHOO,
          o = P.toQueryString(t.params);
        return "".concat(e, "?").concat(o);
      }),
      t.setInitialParams(),
      t
    );
  }
  return n;
})(N);
var Et = (function (a) {
    j(n, a);
    function n(r) {
      var t = a.call(this, r) || this;
      return (
        (t.baseUrl = I.OUTLOOK),
        (t.setInitialParams = function () {
          var e = T.OUTLOOK_DATE;
          t.isAllDay || (e += T.OUTLOOK_TIME),
            t
              .setParam("rru", "addevent")
              .setParam("path", "/calendar/action/compose")
              .setParam("startdt", v.formatDate(t.start, e))
              .setParam("enddt", v.formatDate(t.end, e))
              .setParam("subject", t.title)
              .setParam("body", t.description)
              .setParam("location", t.location)
              .setParam("allday", t.isAllDay.toString()),
            t.attendees.length > 0 && t.setParam("to", P.toMailtoList(t.attendees).join(","));
        }),
        (t.setHost = function (e) {
          return ["live", "office"].includes(e) && (t.baseUrl = I.OUTLOOK.replace("{{host}}", e)), t;
        }),
        (t.render = function () {
          var e = P.toQueryString(t.params);
          return "".concat(t.baseUrl, "?").concat(e);
        }),
        t.setInitialParams(),
        t.setHost("live"),
        t
      );
    }
    return n;
  })(N),
  Dt = (function (a) {
    j(n, a);
    function n(r) {
      var t = a.call(this, r) || this;
      return (
        (t.additionalEvents = []),
        (t.properties = []),
        (t.meta = {}),
        (t.setInitialParams = function () {
          t
            .setMeta("UID", y.getUid())
            .setMeta("DTSTAMP", v.getTimeCreated())
            .addProperty("CLASS", "PUBLIC")
            .addProperty("DESCRIPTION", y.formatText(t.description))
            .addProperty("LOCATION", y.formatText(t.location))
            .addProperty("SUMMARY", y.formatText(t.title))
            .addProperty("TRANSP", "TRANSPARENT"),
            t.isAllDay
              ? t
                  .addProperty("DTSTART;VALUE=DATE", v.formatDateNoUtc(t.start, T.DATE))
                  .addProperty("DTEND;VALUE=DATE", v.formatDateNoUtc(v.incrementDate(t.start, 1), T.DATE))
              : t
                  .addProperty("DTSTART", v.formatDate(t.start, T.FULL))
                  .addProperty("DTEND", v.formatDate(t.end, T.FULL)),
            t.recurrence && t.addProperty("RRULE", y.getRrule(t.recurrence)),
            t.attendees.length > 0 &&
              t.attendees.forEach(function (e) {
                var o = e.email,
                  i = e.name,
                  l = e.icsOptions,
                  p = l === void 0 ? {} : l,
                  s = t.getAttendeeParams(p, i),
                  c = "MAILTO:".concat(o);
                t.addProperty(s, c);
              });
        }),
        (t.getAttendeeParams = function (e, o) {
          var i = {};
          o && (i.CN = o),
            e.delegatedFrom && (i["DELEGATED-FROM"] = e.delegatedFrom),
            e.partStat && (i.PARTSTAT = e.partStat),
            e.role && (i.ROLE = e.role),
            e.sentBy && (i["SENT-BY"] = e.sentBy),
            (i.RSVP = e.rsvp ? "TRUE" : "FALSE");
          var l = P.toParamString(i, ";");
          return "ATTENDEE;".concat(l);
        }),
        (t.getAlarmDuration = function (e) {
          var o = [
            "".concat(e.weeks, "W"),
            "".concat(e.days, "D"),
            "".concat(e.hours, "H"),
            "".concat(e.minutes, "M"),
            "".concat(e.seconds, "S"),
          ].filter(function (i) {
            return /^[0-9]+[A-Z]$/.exec(i);
          });
          return o.unshift(e.after ? "PT" : "-PT"), o.join("");
        }),
        (t.getMeta = function () {
          return Object.keys(t.meta).map(function (e) {
            return "".concat(e, ":").concat(t.meta[e]);
          });
        }),
        (t.setMeta = function (e, o) {
          return (t.meta[e] = o), t;
        }),
        (t.addEvent = function (e) {
          return t.additionalEvents.push(e), t;
        }),
        (t.addProperty = function (e, o) {
          if (typeof o == "object") {
            t.properties.push("BEGIN:".concat(e));
            for (var i in o) t.addProperty(i, o[i]);
            t.properties.push("END:".concat(e));
          } else t.properties.push("".concat(e, ":").concat(o.toString()));
          return t;
        }),
        (t.addAlarm = function (e) {
          var o = { ACTION: e.action };
          if (
            (e.description && (o.DESCRIPTION = y.formatText(e.description)),
            e.summary && (o.SUMMARY = y.formatText(e.summary)),
            e.duration && (o.DURATION = t.getAlarmDuration(e.duration)),
            e.repeat && (o.REPEAT = e.repeat),
            e.attach)
          ) {
            var i = e.attach.params ? "ATTACH;".concat(e.attach.params) : "ATTACH";
            o[i] = e.attach.url;
          }
          return (
            e.trigger instanceof Date
              ? (o["TRIGGER;VALUE=DATE-TIME"] = v.formatDate(e.trigger, T.FULL))
              : (o.TRIGGER = t.getAlarmDuration(e.trigger)),
            t.addProperty("VALARM", o)
          );
        }),
        (t.render = function () {
          var e = L([t], t.additionalEvents, !0),
            o = e.reduce(function (i, l) {
              return L(
                L(L(L(L([], i, !0), ["BEGIN:VEVENT"], !1), l.properties, !0), l.getMeta(), !0),
                ["END:VEVENT"],
                !1,
              );
            }, []);
          return L(L(["BEGIN:VCALENDAR", "VERSION:2.0"], o, !0), ["PRODID:".concat(y.getProdId()), "END:VCALENDAR"], !1)
            .join(`
`);
        }),
        t.setInitialParams(),
        t
      );
    }
    return n;
  })(N),
  W = { exports: {} };
(function (a, n) {
  (function (r, t) {
    t();
  })(C, function () {
    function r(s, c) {
      return (
        typeof c > "u"
          ? (c = { autoBom: !1 })
          : typeof c != "object" &&
            (console.warn("Deprecated: Expected third argument to be a object"), (c = { autoBom: !c })),
        c.autoBom && /^\s*(?:text\/\S*|application\/xml|\S*\/\S*\+xml)\s*;.*charset\s*=\s*utf-8/i.test(s.type)
          ? new Blob(["\uFEFF", s], { type: s.type })
          : s
      );
    }
    function t(s, c, d) {
      var u = new XMLHttpRequest();
      u.open("GET", s),
        (u.responseType = "blob"),
        (u.onload = function () {
          p(u.response, c, d);
        }),
        (u.onerror = function () {
          console.error("could not download file");
        }),
        u.send();
    }
    function e(s) {
      var c = new XMLHttpRequest();
      c.open("HEAD", s, !1);
      try {
        c.send();
      } catch {}
      return 200 <= c.status && 299 >= c.status;
    }
    function o(s) {
      try {
        s.dispatchEvent(new MouseEvent("click"));
      } catch {
        var c = document.createEvent("MouseEvents");
        c.initMouseEvent("click", !0, !0, window, 0, 0, 0, 80, 20, !1, !1, !1, !1, 0, null), s.dispatchEvent(c);
      }
    }
    var i =
        typeof window == "object" && window.window === window
          ? window
          : typeof self == "object" && self.self === self
            ? self
            : typeof C == "object" && C.global === C
              ? C
              : void 0,
      l =
        i.navigator &&
        /Macintosh/.test(navigator.userAgent) &&
        /AppleWebKit/.test(navigator.userAgent) &&
        !/Safari/.test(navigator.userAgent),
      p =
        i.saveAs ||
        (typeof window != "object" || window !== i
          ? function () {}
          : "download" in HTMLAnchorElement.prototype && !l
            ? function (s, c, d) {
                var u = i.URL || i.webkitURL,
                  m = document.createElement("a");
                (c = c || s.name || "download"),
                  (m.download = c),
                  (m.rel = "noopener"),
                  typeof s == "string"
                    ? ((m.href = s),
                      m.origin === location.origin ? o(m) : e(m.href) ? t(s, c, d) : o(m, (m.target = "_blank")))
                    : ((m.href = u.createObjectURL(s)),
                      setTimeout(function () {
                        u.revokeObjectURL(m.href);
                      }, 4e4),
                      setTimeout(function () {
                        o(m);
                      }, 0));
              }
            : "msSaveOrOpenBlob" in navigator
              ? function (s, c, d) {
                  if (((c = c || s.name || "download"), typeof s != "string")) navigator.msSaveOrOpenBlob(r(s, d), c);
                  else if (e(s)) t(s, c, d);
                  else {
                    var u = document.createElement("a");
                    (u.href = s),
                      (u.target = "_blank"),
                      setTimeout(function () {
                        o(u);
                      });
                  }
                }
              : function (s, c, d, u) {
                  if (
                    ((u = u || open("", "_blank")),
                    u && (u.document.title = u.document.body.innerText = "downloading..."),
                    typeof s == "string")
                  )
                    return t(s, c, d);
                  var m = s.type === "application/octet-stream",
                    g = /constructor/i.test(i.HTMLElement) || i.safari,
                    _ = /CriOS\/[\d]+/.test(navigator.userAgent);
                  if ((_ || (m && g) || l) && typeof FileReader < "u") {
                    var O = new FileReader();
                    (O.onloadend = function () {
                      var h = O.result;
                      (h = _ ? h : h.replace(/^data:[^;]*;/, "data:attachment/file;")),
                        u ? (u.location.href = h) : (location = h),
                        (u = null);
                    }),
                      O.readAsDataURL(s);
                  } else {
                    var Y = i.URL || i.webkitURL,
                      A = Y.createObjectURL(s);
                    u ? (u.location = A) : (location.href = A),
                      (u = null),
                      setTimeout(function () {
                        Y.revokeObjectURL(A);
                      }, 4e4);
                  }
                });
    (i.saveAs = p.saveAs = p), (a.exports = p);
  });
})(W);
var At = W.exports;
const yt = at(At);
function Lt(a) {
  let n,
    r,
    t,
    e,
    o,
    i,
    l,
    p,
    s = "Download iCal Event",
    c,
    d,
    u,
    m,
    g,
    _,
    O,
    Y;
  return {
    c() {
      (n = U("div")),
        (r = U("button")),
        (t = U("i")),
        (e = F(" Export event")),
        (i = B()),
        (l = U("div")),
        (p = U("button")),
        (p.textContent = s),
        (c = B()),
        (d = U("a")),
        (u = F("Add to Google Calendar")),
        (m = B()),
        (g = U("a")),
        (_ = F("Add to Microsoft Outlook")),
        this.h();
    },
    l(A) {
      n = w(A, "DIV", { class: !0, role: !0 });
      var h = S(n);
      r = w(h, "BUTTON", {
        type: !0,
        class: !0,
        href: !0,
        "data-bs-toggle": !0,
        "aria-haspopup": !0,
        "aria-expanded": !0,
      });
      var x = S(r);
      (t = w(x, "I", { class: !0, "aria-hidden": !0 })),
        S(t).forEach(R),
        (e = H(x, " Export event")),
        x.forEach(R),
        (i = k(h)),
        (l = w(h, "DIV", { class: !0 }));
      var M = S(l);
      (p = w(M, "BUTTON", { class: !0, "data-svelte-h": !0 })),
        $(p) !== "svelte-bawtft" && (p.textContent = s),
        (c = k(M)),
        (d = w(M, "A", { class: !0, href: !0, target: !0, rel: !0 }));
      var K = S(d);
      (u = H(K, "Add to Google Calendar")),
        K.forEach(R),
        (m = k(M)),
        (g = w(M, "A", { class: !0, href: !0, target: !0, rel: !0 }));
      var q = S(g);
      (_ = H(q, "Add to Microsoft Outlook")), q.forEach(R), M.forEach(R), h.forEach(R), this.h();
    },
    h() {
      f(t, "class", "far fa-calendar-plus me-1"),
        f(t, "aria-hidden", "true"),
        f(r, "type", "button"),
        f(r, "class", (o = "btn dropdown-toggle " + a[0])),
        f(r, "href", "#"),
        f(r, "data-bs-toggle", "dropdown"),
        f(r, "aria-haspopup", "true"),
        f(r, "aria-expanded", "false"),
        f(p, "class", "dropdown-item"),
        f(d, "class", "dropdown-item"),
        f(d, "href", a[1]),
        f(d, "target", "_blank"),
        f(d, "rel", "noreferrer"),
        f(g, "class", "dropdown-item"),
        f(g, "href", a[2]),
        f(g, "target", "_blank"),
        f(g, "rel", "noreferrer"),
        f(l, "class", "dropdown-menu"),
        f(n, "class", "dropwdown btn-group"),
        f(n, "role", "group");
    },
    m(A, h) {
      tt(A, n, h),
        D(n, r),
        D(r, t),
        D(r, e),
        D(n, i),
        D(n, l),
        D(l, p),
        D(l, c),
        D(l, d),
        D(d, u),
        D(l, m),
        D(l, g),
        D(g, _),
        O || ((Y = et(p, "click", a[5])), (O = !0));
    },
    p(A, [h]) {
      h & 1 && o !== (o = "btn dropdown-toggle " + A[0]) && f(r, "class", o);
    },
    i: Q,
    o: Q,
    d(A) {
      A && R(n), (O = !1), Y();
    },
  };
}
function Pt(a, n, r) {
  const { saveAs: t } = yt;
  let { frontmatter: e = {} } = n,
    { add_class: o = "btn-outline-success" } = n,
    i = "";
  typeof e.locationURL == "string" ? (i = e.locationURL) : e.locationURL && (i = e.locationURL.join(", "));
  const l = { title: e.title, description: e.subtitle, start: e.start, end: e.end, location: i };
  l.start === void 0 && (l.start = new Date(l.startDate + "T" + l.startTime)),
    l.end === void 0 && (l.end = new Date(l.endDate + "T" + l.endTime));
  const p = new Tt(l).render(),
    s = new Et(l).render();
  let c = new Dt(l).render();
  const d = new Blob([c], { type: "text/calendar;charset=utf-8" });
  function u() {
    t(d, e.title.replace(/[^a-z0-9]/gi, "_").toLowerCase() + ".ics");
  }
  const m = () => u();
  return (
    (a.$$set = (g) => {
      "frontmatter" in g && r(4, (e = g.frontmatter)), "add_class" in g && r(0, (o = g.add_class));
    }),
    [o, p, s, u, e, m]
  );
}
class wt extends X {
  constructor(n) {
    super(), z(this, n, Pt, Lt, J, { frontmatter: 4, add_class: 0 });
  }
}
export { wt as default };
