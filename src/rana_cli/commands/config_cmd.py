from .. import config as config_mod
from ..output import print_json
from ._shared import add_env_tenant_args


def register(subparsers):
    p = subparsers.add_parser("config", help="inspect resolved configuration")
    sub = p.add_subparsers(dest="config_command", required=True)

    p_show = sub.add_parser("show", help="print the resolved config for an environment")
    add_env_tenant_args(p_show)
    p_show.set_defaults(func=cmd_show)

    p_envs = sub.add_parser("environments", help="list known environment names")
    p_envs.set_defaults(func=cmd_environments)

    p_path = sub.add_parser("path", help="print where config/tokens are stored on disk")
    p_path.set_defaults(func=cmd_path)


def cmd_show(args):
    cfg = config_mod.load_config(env=args.env, tenant_override=args.tenant)
    print_json(cfg)


def cmd_environments(args):
    for env in config_mod.list_environments():
        print(env)


def cmd_path(args):
    print(f"config file:  {config_mod.CONFIG_PATH}")
    print(f"tokens file:  {config_mod.TOKENS_PATH}")
