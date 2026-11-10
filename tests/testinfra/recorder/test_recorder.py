# Source: https://github.com/infraguide-org/lab-openstack
# Copyright (c) 2026 infraguide.org, MIT License
"""Recorder profile, for the ARA server set up by scripts/infra/recorder.sh."""

URL = "http://recorder.lab.nfgd.net:8000"


def test_port_8000_listening(host):
    # podman runs ara-server with --network host, so it binds on the host directly
    sockets = host.socket.get_listening_sockets()
    assert any(s.startswith("tcp://") and s.endswith(":8000") for s in sockets), sockets


def test_ara_answers(host):
    # the name has to be in ARA_ALLOWED_HOSTS of /etc/ara/environment
    cmd = host.run(f"curl -sS -f --max-time 10 {URL}")
    assert cmd.rc == 0, cmd.stderr
    assert "ARA Records Ansible" in cmd.stdout, cmd.stdout[:200]
