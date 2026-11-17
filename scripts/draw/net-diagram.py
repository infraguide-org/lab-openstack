#!/usr/bin/env python3
"""Draw a network diagram (SVG) directly from env.yaml.

Single file, three parts: build() turns env.yaml + layout file into a diagram
description, layout()/render() draw it as SVG, main() is the command line.

Usage:
    python3 netdiagram.py env.yaml layout.yaml out.svg [--focus ID[,ID...]]

Source of truth is env.yaml (server_conf: hosts and their networks,
network_conf: network addresses). The layout file only adds what env.yaml does
not contain: which hosts and networks to draw, in which order, and how.

The output is deterministic: the same inputs always produce the same SVG.
Render to PNG with:  rsvg-convert -z 1.5 out.svg -o out.png

LAYOUT FILE
-----------
Example showing every available option:

    title: OpenStack Umgebung        # heading of the diagram
    label_width: 230                 # space (px) left of the first host for the
                                     # network labels; default 150
    show_addr: true                  # append the network address from network_conf
                                     # (e.g. 10.20.8.0/24) to the label; default true
    focus: controlplane              # optional: network id (or a list of ids, e.g.
                                     # [controlplane, storage0]) to highlight, see
                                     # FOCUS MODE; can also be set with --focus

    # Only the networks listed here are drawn. Anything else a host is attached
    # to in env.yaml is ignored. The order is the order of the network lines
    # (top to bottom, separately for the "top" and the "bottom" side).
    networks:
      - id: controlplane             # required: key in network_conf of env.yaml
        label: Control Plane         # required: text shown at the network line
        color: "#e8590c"             # required: line color (any SVG color)
        side: top                    # top | bottom (default bottom): draw the network
                                     # above or below the host boxes; hosts connect
                                     # upwards to "top" and downwards to "bottom" networks
        style: normal                # normal | grey (default normal): "grey" draws the
                                     # network (line, label, dots) in light grey,
                                     # e.g. for networks that are only context

    # Hosts are drawn left to right in groups, in this order. Every group gets a
    # dashed frame with its name.
    host_groups:
      - name: Controller             # group name shown in the frame
        hosts: ["controller*"]       # host names or shell-style patterns (fnmatch)
                                     # matched against hostname in server_conf; hosts
                                     # keep the order they have in env.yaml; a pattern
                                     # that matches nothing is an error
      - name: Compute
        hosts: ["compute*"]
        scalable: true               # growing group: only the first and the last
                                     # matching host are drawn, with "..." in between
                                     # (skipped hosts are listed on stderr);
                                     # no effect with two or fewer hosts

FOCUS MODE
----------
With `focus: <id>` or a list `focus: [<id>, <id>, ...]` (command line:
--focus id1,id2) the focus networks stay in their colors and are drawn thicker,
together with the connections of the hosts attached to them. All other networks,
their connection dots and the hosts that are attached to NO focus network are
drawn in grey. If a host is attached to several focus networks, its line is drawn
in the color of the nearest one and continues in the color of the next one.
The diagram title gets a " - Fokus: <label>, <label>" suffix. The command line
option overrides `focus:` in the file. Focus networks win over `style: grey`.
"""
import fnmatch
import sys
from xml.sax.saxutils import escape

import yaml

# --- fixed layout parameters (all deterministic, no random values) ---
FONT = "DejaVu Sans, Arial, sans-serif"
MARGIN = 30
LABEL_W = 150        # space on the left for network labels
BOX_W, BOX_H = 120, 40
HOST_GAP = 24        # distance between hosts inside a group
GROUP_GAP = 56       # distance between groups
GAP_W = 40           # width of the "..." placeholder
GROUP_PAD = 10       # padding of the group frame
TITLE_H = 40
GROUP_LABEL_H = 22
NET_TOP_GAP = 50     # distance host boxes -> first network
NET_STEP = 60        # distance between networks
NET_BOTTOM = 40
DOT_R = 6


# ---------------------------------------------------------------------------
# 1. env.yaml + layout file -> diagram description
# ---------------------------------------------------------------------------
def build(env, lay):
    """Translate env.yaml + layout into the structure that render() draws."""
    hosts = {h["hostname"]: h for h in env["server_conf"]}
    netconf = env["network_conf"]
    shown = {n["id"] for n in lay["networks"]}

    for n in lay["networks"]:
        if n.get("style", "normal") not in ("normal", "grey"):
            raise SystemExit(f"Network '{n['id']}': style must be normal or grey")
        if n["id"] not in netconf:
            raise SystemExit(f"Network '{n['id']}' is missing in network_conf")

    nets = []
    for n in lay["networks"]:
        addr = netconf[n["id"]].get("addr")
        nets.append({
            "id": n["id"], "label": n["label"], "color": n["color"],
            "side": n.get("side", "bottom"),
            "grey": n.get("style", "normal") == "grey",
            "sub": addr if lay.get("show_addr", True) and addr else "",
        })

    groups = []
    for g in lay["host_groups"]:
        matched = []
        for pat in g["hosts"]:
            names = [h for h in hosts if fnmatch.fnmatch(h, pat)]
            if not names:
                raise SystemExit(f"No host matches '{pat}'")
            matched += [x for x in names if x not in matched]

        shown_hosts = matched
        gh = []
        if g.get("scalable") and len(matched) > 2:
            # scalable group: only the first and the last host, "..." in between
            shown_hosts = [matched[0], matched[-1]]
            skipped = matched[1:-1]
            print(f"{g['name']}: {len(matched)} hosts, showing {shown_hosts[0]} and "
                  f"{shown_hosts[1]}, skipped: {', '.join(skipped)}", file=sys.stderr)
        for i, name in enumerate(shown_hosts):
            if g.get("scalable") and len(matched) > 2 and i == 1:
                gh.append({"gap": True})
            gh.append({"name": name,
                       "nets": [x for x in hosts[name]["networks"] if x in shown]})
        groups.append({"name": g["name"], "hosts": gh})

    focus = lay.get("focus")
    focus = [focus] if isinstance(focus, str) else list(focus or [])
    for f in focus:
        if f not in shown:
            raise SystemExit(f"Focus network '{f}' is not listed under 'networks'")
    title = lay["title"]
    if focus:
        labels = [n["label"] for n in lay["networks"] if n["id"] in focus]
        title = f"{title} \u2013 Fokus: {', '.join(labels)}"
    return {"title": title, "label_width": lay.get("label_width", 150),
            "focus": focus, "networks": nets, "groups": groups}


# ---------------------------------------------------------------------------
# 2. diagram description -> SVG
# ---------------------------------------------------------------------------
def layout(cfg):
    """Compute the x positions of all hosts. Returns (items, groups, width)."""
    x = MARGIN + cfg.get("label_width", LABEL_W)
    items, groups = [], []
    for gi, g in enumerate(cfg["groups"]):
        if gi:
            x += GROUP_GAP
        gx0 = x
        for hi, h in enumerate(g["hosts"]):
            if hi:
                x += HOST_GAP
            if h.get("gap"):
                items.append({"gap": True, "x": x, "w": GAP_W})
                x += GAP_W
            else:
                items.append({**h, "x": x, "w": BOX_W})
                x += BOX_W
        groups.append({"name": g["name"], "x0": gx0, "x1": x})
    return items, groups, x + MARGIN


def render(cfg):
    nets = cfg["networks"]
    items, groups, width = layout(cfg)
    ids = [n["id"] for n in nets]
    for it in items:
        for n in it.get("nets", []):
            if n not in ids:
                raise SystemExit(f"Unknown network '{n}' at host {it.get('name')}")

    top = [n for n in nets if n.get("side", "bottom") == "top"]
    bottom = [n for n in nets if n.get("side", "bottom") != "top"]

    # vertical layout: title, networks on top, host row (with group frames), networks below
    y = TITLE_H + (NET_TOP_GAP - 10 if top else 0)
    net_y = {}
    for i, n in enumerate(top):
        net_y[n["id"]] = y + i * NET_STEP
    y_frame = (net_y[top[-1]["id"]] + NET_TOP_GAP) if top else TITLE_H
    y_box = y_frame + GROUP_LABEL_H + GROUP_PAD
    y_frame_h = GROUP_LABEL_H + BOX_H + 2 * GROUP_PAD
    y_b0 = y_frame + y_frame_h + NET_TOP_GAP
    for i, n in enumerate(bottom):
        net_y[n["id"]] = y_b0 + i * NET_STEP
    last = y_b0 + (len(bottom) - 1) * NET_STEP if bottom else y_frame + y_frame_h
    height = last + NET_BOTTOM

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
      f'width="{width}" height="{height}" font-family="{FONT}">')
    a(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')
    a(f'<text x="{MARGIN}" y="26" font-size="20" font-weight="bold" fill="#212529">'
      f'{escape(cfg.get("title", ""))}</text>')

    # group frames (label inside, top left)
    for g in groups:
        gx, gw = g["x0"] - GROUP_PAD, g["x1"] - g["x0"] + 2 * GROUP_PAD
        a(f'<rect x="{gx}" y="{y_frame}" width="{gw}" height="{y_frame_h}" rx="8" '
          f'fill="none" stroke="#adb5bd" stroke-dasharray="4 4"/>')
        a(f'<text x="{gx + 8}" y="{y_frame + 16}" font-size="12" fill="#868e96">'
          f'{escape(g["name"])}</text>')

    # --- focus mode: one or more networks in color, everything else grey -----
    focus = cfg.get("focus")
    focus_ids = [focus] if isinstance(focus, str) else list(focus or [])
    for f in focus_ids:
        if f not in ids:
            raise SystemExit(f"Focus network '{f}' is not in the diagram")
    G_LINE, G_DOT, G_TXT, G_BOX = "#ced4da", "#dee2e6", "#adb5bd", "#f8f9fa"

    def is_on(n):
        return n["id"] in focus_ids or (not focus_ids and not n.get("grey"))

    def net_color(n):
        return n["color"] if is_on(n) else G_LINE

    def draw_net(n):
        ny = net_y[n["id"]]
        on = is_on(n)
        w = 4 if n["id"] in focus_ids else (3 if on else 2)
        a(f'<line x1="{MARGIN}" y1="{ny}" x2="{width - MARGIN}" y2="{ny}" '
          f'stroke="{net_color(n)}" stroke-width="{w}"/>')
        sub = (f'<tspan dx="8" font-size="11" font-weight="normal" '
               f'fill="{"#868e96" if on else G_TXT}">{escape(n["sub"])}</tspan>'
               ) if n.get("sub") else ""
        a(f'<text x="{MARGIN}" y="{ny - 8}" font-size="13" font-weight="bold" '
          f'fill="{n["color"] if on else G_TXT}">{escape(n["label"])}{sub}</text>')

    hosts = [it for it in items if not it.get("gap")]

    # networks (focus networks are drawn last so that they lie on top)
    for n in nets:
        if n["id"] not in focus_ids:
            draw_net(n)

    # host lines and dots
    for it in items:
        if it.get("gap"):
            cy = y_box + BOX_H / 2
            cx = it["x"] + it["w"] / 2
            for d in (-10, 0, 10):
                a(f'<circle cx="{cx + d}" cy="{cy}" r="2.5" '
                  f'fill="{"#495057" if not focus_ids else G_TXT}"/>')
            continue
        cx = it["x"] + it["w"] / 2
        hn = [n for n in nets if n["id"] in it["nets"]]
        ht = [n for n in hn if n in top]
        hb = [n for n in hn if n in bottom]
        lc = "#495057" if not focus_ids else G_LINE
        if ht:
            y_first = min(net_y[n["id"]] for n in ht)
            a(f'<line x1="{cx}" y1="{y_first}" x2="{cx}" y2="{y_box}" '
              f'stroke="{lc}" stroke-width="2"/>')
        if hb:
            y_last = max(net_y[n["id"]] for n in hb)
            a(f'<line x1="{cx}" y1="{y_box + BOX_H}" x2="{cx}" y2="{y_last}" '
              f'stroke="{lc}" stroke-width="2"/>')
        for n in hn:
            if n["id"] in focus_ids:
                continue
            fill, st = (n["color"], "#212529") if is_on(n) else (G_DOT, G_TXT)
            a(f'<circle cx="{cx}" cy="{net_y[n["id"]]}" r="{DOT_R}" '
              f'fill="{fill}" stroke="{st}" stroke-width="1.5"/>')

    if focus_ids:
        fnets = [n for n in nets if n["id"] in focus_ids]
        for n in fnets:
            draw_net(n)

        def dist(n):      # distance from the host box to the network line
            return (y_box - net_y[n["id"]]) if n in top else (net_y[n["id"]] - (y_box + BOX_H))

        for it in hosts:
            cx = it["x"] + it["w"] / 2
            conn = [n for n in fnets if n["id"] in it["nets"]]
            # farthest first, so that the nearest focus network's color lies on top
            for n in sorted(conn, key=dist, reverse=True):
                y0 = y_box if n in top else y_box + BOX_H
                a(f'<line x1="{cx}" y1="{y0}" x2="{cx}" y2="{net_y[n["id"]]}" '
                  f'stroke="{n["color"]}" stroke-width="3"/>')
        for it in hosts:
            cx = it["x"] + it["w"] / 2
            for n in fnets:
                if n["id"] in it["nets"]:
                    a(f'<circle cx="{cx}" cy="{net_y[n["id"]]}" r="{DOT_R + 1}" '
                      f'fill="{n["color"]}" stroke="#212529" stroke-width="2"/>')

    # host boxes
    for it in hosts:
        cx = it["x"] + it["w"] / 2
        dim = bool(focus_ids) and not any(f in it["nets"] for f in focus_ids)
        fill, st, tx = ("#e6fcf5", "#212529", "#212529") if not dim else (G_BOX, G_TXT, G_TXT)
        a(f'<rect x="{it["x"]}" y="{y_box}" width="{BOX_W}" height="{BOX_H}" rx="8" '
          f'fill="{fill}" stroke="{st}" stroke-width="2"/>')
        a(f'<text x="{cx}" y="{y_box + BOX_H / 2 + 5}" font-size="15" '
          f'text-anchor="middle" fill="{tx}">{escape(it["name"])}</text>')

    a("</svg>")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------------------
# 3. command line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    args = sys.argv[1:]
    focus = None
    if "--focus" in args:
        i = args.index("--focus")
        focus = args[i + 1]
        del args[i:i + 2]
    if len(args) != 3:
        raise SystemExit(__doc__)
    env = yaml.safe_load(open(args[0], encoding="utf-8"))
    lay = yaml.safe_load(open(args[1], encoding="utf-8"))
    if focus:
        lay["focus"] = focus.split(",")      # command line overrides the layout file
    svg = render(build(env, lay))
    with open(args[2], "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
