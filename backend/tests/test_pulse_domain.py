"""The live lab view's pure logic: link rates, the activity filter, node processes."""

from domain import monitor as m
from domain import pulse
from engine.base import IfaceCounters

LINK = {
    "connection_id": "c1",
    "from": "a",
    "to": "b",
    "endpoints": [{"node": "b", "interface": "eth0"}, {"node": "a", "interface": "eth1"}],
}


def _c(tx_packets=0, rx_packets=0, tx_bytes=0, rx_bytes=0):
    return IfaceCounters(
        tx_packets=tx_packets, rx_packets=rx_packets, tx_bytes=tx_bytes, rx_bytes=rx_bytes
    )


def test_link_rates_read_the_from_side():
    prev = {"a": {"eth1": _c()}, "b": {"eth0": _c()}}
    cur = {"a": {"eth1": _c(20, 4, 20_000, 400)}, "b": {"eth0": _c(4, 20, 400, 20_000)}}
    rate = pulse.link_rates([LINK], prev, cur, 2.0)["c1"]
    assert (rate.fwd_pps, rate.rev_pps) == (10, 2) and rate.pps == 12
    assert (rate.fwd_bps, rate.rev_bps) == (80_000, 1600)


def test_link_rates_fall_back_to_the_far_end_swapped():
    prev, cur = {"b": {"eth0": _c()}}, {"b": {"eth0": _c(4, 20, 400, 20_000)}}
    rate = pulse.link_rates([LINK], prev, cur, 1.0)["c1"]
    assert (rate.fwd_pps, rate.rev_pps) == (20, 4)  # what b received went forward


def test_link_rates_skip_resets_unknown_links_and_no_time():
    prev = {"a": {"eth1": _c(50, 50, 5000, 5000)}}
    cur = {"a": {"eth1": _c(1, 1, 100, 100)}}  # the interface was recreated
    assert pulse.link_rates([LINK], prev, cur, 1.0) == {}
    assert pulse.link_rates([{**LINK, "connection_id": None}], cur, cur, 1.0) == {}
    assert pulse.link_rates([LINK], cur, cur, 0.0) == {}


def test_leg_attachments_get_the_id_the_editor_draws_them_with():
    data = {
        "sites": [
            {
                "id": "s",
                "subnets": [
                    {
                        "id": "it",
                        "containers": [
                            {"id": "fw", "interfaces": [{"subnetId": "ot", "ip": "10.0.3.1"}]},
                            {"id": "pc"},
                        ],
                    },
                    {"id": "ot", "containers": [{"id": "ot-sw"}, {"id": "rtu"}]},
                ],
            }
        ]
    }
    links = [
        {"connection_id": "c1", "from": "pc", "to": "fw", "endpoints": []},
        {"connection_id": None, "from": "fw", "to": "ot-sw", "endpoints": []},  # fw's leg
        {"connection_id": None, "from": "pc", "to": "rtu", "endpoints": []},  # no such leg
    ]
    keyed = pulse.keyed_links(links, data)
    assert [link["connection_id"] for link in keyed] == ["c1", "leg:fw:ot"]
    assert links[1]["connection_id"] is None  # the saved links are left alone


def _rate(pps, fwd_bps=1000.0, rev_bps=1000.0):
    return {"c1": pulse.LinkRate(pps / 2, pps / 2, fwd_bps, rev_bps)}


def test_a_lone_exchange_does_not_light_a_link_but_a_ping_does():
    act = pulse.LinkActivity()
    assert act.update(_rate(2), 0) == {}  # an ARP request and its reply
    for t in range(1, 7):
        assert act.update(_rate(0), t) == {}
    assert act.update(_rate(2), 7) == {}  # a ping: two packets a second…
    assert act.update(_rate(2), 8) == {"c1": "both"}  # …that keeps coming


def test_a_poll_every_other_second_is_steady_traffic():
    act = pulse.LinkActivity()
    seen = [act.update(_rate(7 if t % 2 == 0 else 0), t) for t in range(12)]
    assert seen[:2] == [{}, {}] and all(s == {"c1": "both"} for s in seen[2:])


def test_an_active_link_holds_through_a_gap_then_goes_quiet():
    act = pulse.LinkActivity()
    act.update(_rate(10), 0)
    assert act.update(_rate(10), 1) == {"c1": "both"}
    assert act.update(_rate(0), 2) == {"c1": "both"}
    assert act.update(_rate(0), 6) == {"c1": "both"}  # within OFF_AFTER_S of t=1
    assert act.update(_rate(0), 6.5) == {}
    assert act.update(_rate(10), 12) == {}  # has to earn it again
    assert act.update({}, 13) == {}  # the link is gone: so is its state


def test_direction_follows_the_bytes():
    act = pulse.LinkActivity()
    act.update(_rate(100, fwd_bps=1e6, rev_bps=1e4), 0)
    assert act.update(_rate(100, fwd_bps=1e6, rev_bps=1e4), 1) == {"c1": "fwd"}
    act = pulse.LinkActivity()
    act.update(_rate(100, fwd_bps=1e4, rev_bps=1e6), 0)
    assert act.update(_rate(100, fwd_bps=1e4, rev_bps=1e6), 1) == {"c1": "rev"}


def test_display_names_a_script_after_what_it_runs():
    assert pulse.display("zeek", "zeek -i eth0 -C") == ("zeek", "zeek -i eth0 -C")
    assert pulse.display("sh", "sh -lc while sleep 2; do /usr/bin/breaker status; done") == (
        "breaker",
        "while sleep 2; do /usr/bin/breaker status; done",
    )
    assert pulse.display("sh", "sh -lc ping -i 2 10.0.2.5") == ("ping", "ping -i 2 10.0.2.5")
    # Assignments are not what a command line is about.
    assert pulse.display("sh", "sh -lc export TARGET=10.0.2.5; curl -s $TARGET")[0] == "curl"
    assert pulse.display("sh", "sh -lc FOO=1 BAR=x nc -z host 80")[0] == "nc"
    assert pulse.display("bash", "bash -c while :; do date; sleep 1; done")[0] == "date"
    assert pulse.display("bash", "-bash") == ("bash", "-bash")
    assert pulse.display("kworker", "") == ("kworker", "kworker")


def test_node_processes_keep_what_was_started_since_the_deploy():
    rows = [
        [20, 7, 100, "nginx", "nginx: worker"],  # before the deploy finished
        [30, 7, 5000, "bash", "bash -il"],  # an idle terminal (started from outside)
        [31, 30, 5100, "zeek", "zeek -i eth0"],  # typed into it
        [40, 7, 5200, "sh", "sh -lc while sleep 1; do curl -s 10.0.2.5; done"],
        [41, 40, 5300, "sleep", "sleep 1"],  # its child: not listed on its own
        [50, 9, 5400, "sshd", "sshd: root@pts/0"],  # a session of the node's own sshd
        [51, 50, 5450, "bash", "-bash"],
    ]
    procs = pulse.node_processes(7, rows, btime=1000.0, clk_tck=100, since=1040.0)
    assert [(p.pid, p.name, p.via_exec) for p in procs] == [
        (31, "zeek", True),
        (40, "curl", True),
        (50, "sshd", False),
    ]
    assert procs[0].started == 1051.0
    assert procs[0].to_dict() == {"name": "zeek", "args": "zeek -i eth0"}


def test_what_a_terminal_started_shows_once_seen_twice():
    tracker = pulse.ProcessTracker()
    p = pulse.Proc(31, 30, "zeek", "zeek", 1.0)
    blip = pulse.Proc(99, 30, "ls", "ls", 2.0)
    assert tracker.update({"ids": [p, blip]}, 3.0) == {}
    assert tracker.update({"ids": [p]}, 4.0) == {"ids": [p]}
    assert tracker.update({"ids": [blip]}, 5.0) == {}  # gone and back counts from one again


def test_a_loop_typed_into_a_terminal_is_one_steady_entry():
    tracker = pulse.ProcessTracker()
    tracker.update({"hist": [pulse.Proc(100, 30, "sleep", "sleep 1", 1.0)]}, 1.5)
    for pid in (101, 102):  # a new sleep every second, same shell
        shown = tracker.update({"hist": [pulse.Proc(pid, 30, "sleep", "sleep 1", 2.0)]}, 2.5)
        assert [p.to_dict() for p in shown["hist"]] == [{"name": "sleep", "args": "sleep 1"}]


def test_a_services_own_routine_never_shows_but_a_session_does():
    tracker = pulse.ProcessTracker()
    session = pulse.Proc(50, 9, "sshd", "sshd: root@pts/0", 100.0, via_exec=False)
    shown = {}
    for i in range(30):  # the switch's own `sleep 5` loop, and a session that stays
        now = 100.0 + i
        loop = pulse.Proc(200 + i // 5, 1, "sleep", "sleep 5", 100.0 + 5 * (i // 5), via_exec=False)
        shown = tracker.update({"sw": [loop], "hist": [session]}, now)
        assert "sw" not in shown
        assert ("hist" in shown) == (now - 100.0 >= pulse.SETTLED_S)
    assert shown == {"hist": [session]}


def test_payload_lists_only_what_is_happening():
    p = pulse.Proc(31, 30, "zeek", "zeek -i eth0", 1.0)
    assert pulse.payload({"c2": "fwd", "c1": "both"}, {"ids": [p], "hmi": []}) == {
        "type": "pulse",
        "links": {"c1": "both", "c2": "fwd"},
        "nodes": {"ids": [{"name": "zeek", "args": "zeek -i eth0"}]},
    }


def test_sweeps_carry_processes_and_older_lines_still_parse():
    old = '{"v":1,"t":5,"c":{"aaaaaaaaaaaa":[1,2,0,null,1,0,{}]}}'
    new = (
        '{"v":1,"t":5,"btime":1000,"c":{"aaaaaaaaaaaa":'
        '[1,2,0,null,1,0,{},[7,[[31,30,5100,"zeek","zeek -i eth0"]]]]}}'
    )
    assert m.parse_line(old).procs == {} and m.parse_line(old).btime is None
    sweep = m.parse_line(new)
    assert sweep.btime == 1000
    assert sweep.procs == {"aaaaaaaaaaaa": (7, [[31, 30, 5100, "zeek", "zeek -i eth0"]])}
