from . import (auth, call, config_cmd, datasets, digest, files, invitations, jobs,
               projects, publications, shell, tenants, users)

ALL_MODULES = [
    auth, config_cmd, call,
    projects, datasets, publications, files, jobs, invitations, users, tenants,
    shell, digest,
]


def register_all(subparsers):
    for module in ALL_MODULES:
        module.register(subparsers)
