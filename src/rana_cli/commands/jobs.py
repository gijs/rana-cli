from ._shared import add_env_tenant_args, add_pagination_args, emit, get_client, pagination_query


def register(subparsers):
    p = subparsers.add_parser("jobs", help="inspect async jobs")
    sub = p.add_subparsers(dest="jobs_command", required=True)

    p_list = sub.add_parser("list", help="list jobs")
    add_env_tenant_args(p_list)
    add_pagination_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a job")
    add_env_tenant_args(p_get)
    p_get.add_argument("job_id")
    p_get.set_defaults(func=cmd_get)

    p_logs = sub.add_parser("logs", help="show job logs")
    add_env_tenant_args(p_logs)
    p_logs.add_argument("job_id")
    p_logs.set_defaults(func=cmd_logs)

    p_results = sub.add_parser("results", help="show job results")
    add_env_tenant_args(p_results)
    p_results.add_argument("job_id")
    p_results.set_defaults(func=cmd_results)


def cmd_list(args):
    client = get_client(args)
    emit(client.get("/tenants/{tenant_id}/jobs", query=pagination_query(args)))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/jobs/{args.job_id}"))


def cmd_logs(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/jobs/{args.job_id}/logs"))


def cmd_results(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/jobs/{args.job_id}/results"))
