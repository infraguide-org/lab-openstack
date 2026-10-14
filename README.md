# lab-openstack

Deploy and operate a multi-node OpenStack cloud with kolla-ansible and Ceph.
The lab runs on one bare-metal host, the cluster nodes are virtual machines.

Lab description: [infraguide.org/learn/openstack](https://infraguide.org/learn/openstack/)

This repository holds the configuration, the deployment code, the modules and the slides of the lab.
The hypervisor, the networks and the virtual machines of the environment are created with
[setup-sandbox](https://github.com/infraguide-org/setup-sandbox). This repository is used to:
* Deploy OpenStack and Ceph on the virtual machines
* Create and publish the slides
* Run the workshop using the slides

## Repository layout
| Path | Content |
|---|---|
| `conf/` | `env.yaml` - network and host layout of the environment, `tmuxp.yaml` - tmux session with a window per host group |
| `deploy/kolla-ansible/` | kolla-ansible inventory (`inventory/lab`) and configuration (`custom-config/lab`) |
| `deploy/cephadm/` | cephadm configuration of the Ceph cluster |
| `modules/` | additional modules: `automation` (Ansible, Terraform, testinfra) and `testing` (Tempest) |
| `scripts/` | helper scripts for the nodes (`helpers`, `infra`) |
| `slides/` | slide sources (`src`) and the script that builds the index page and `index.json` (`scripts`) |
| `status/` | `build.yml` - result of the automatic lab build, shown on the lab page |

## Environment
Network:

![Network](slides/src/assets/openstack-workshop.drawio.svg)

OpenStack:

![OpenStack](slides/src/assets/openstack-environment.drawio.svg)

Ceph:

![Ceph](slides/src/assets/ceph-environment.drawio.svg)

## Slides
The slides are published on GitHub Pages: [infraguide-org.github.io/lab-openstack](https://infraguide-org.github.io/lab-openstack/)

| Deck | Content | Files |
|---|---|---|
| Introduction | OpenStack and Ceph introduction | `slides-introduction` |
| Deploy | Deploy and operate a multi-node OpenStack cloud | `slides-deploy` |
| Automation | Automating the cloud with cloud-init, Ansible and Terraform | `slides-automation` |
| Testing | Automated testing of the cloud | `slides-testing` |

Every deck is available as HTML, PDF and PPTX, for example
`https://infraguide-org.github.io/lab-openstack/slides-deploy.pdf`.
[`index.json`](https://infraguide-org.github.io/lab-openstack/index.json) lists the decks in their order, all files, the hosts of the environment (`hosts`) and the path of the environment diagram (`diagram`) in a machine-readable form.
The slides are also part of [infraguide.org](https://infraguide.org/learn/openstack/).

## How to create slides
The sources are Markdown files in `slides/src`, rendered with [Marp](https://marp.app/):

```bash
cd slides/src
marp          # html
marp --pdf    # pdf
marp --pptx   # pptx
```

The output goes to `slides/dist`. Every push to `main` that changes `slides/src`, `slides/scripts`, `conf/env.yaml`
or `status/` builds the slides and the index page and publishes them with the workflow `.github/workflows/slides.yml`.
The order of the decks is set by the `order` field in the front matter of each deck.
