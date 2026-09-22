from . import (auth, call, config_cmd, datasets, files, invitations, jobs,
               projects, publications, tenants, users)

ALL_MODULES = [
    auth, config_cmd, call,
    projects, datasets, publications, files, jobs, invitations, users, tenants,
]


def register_all(subparsers):
    for module in ALL_MODULES:
        module.register(subparsers)
