import click
from hivemind_core.database import ClientDatabase
from json_database import JsonStorageXDG
from ovos_utils.log import LOG

from multimind import MultiMind


@click.group()
def multimind_cmds():
    pass


@multimind_cmds.command(help="launch MultiMind", name="start")
def main():
    service = MultiMind()
    service.run()


@multimind_cmds.command(help="add a skill to an access key", name="allow-skill")
@click.argument("skill", required=True, type=str)
@click.argument("access_key", required=True, type=str)
def allow_skill(skill_id, access_key):
    user = ClientDatabase().get_client_by_api_key(access_key)
    if not user:
        LOG.error("invalid api key, no such hivemind client")
        return

    db = JsonStorageXDG("multimind", subfolder="hivemind")
    if access_key not in db:
        db[access_key] = [skill_id]
    else:
        db[access_key].append(skill_id)
    db.store()

    print("Allowed skills:", db[access_key])


@multimind_cmds.command(help="remove a skill from an access key", name="remove-skill")
@click.argument("skill", required=True, type=str)
@click.argument("access_key", required=True, type=str)
def disallow_skill(skill_id, access_key):
    db = JsonStorageXDG("multimind", subfolder="hivemind")
    if access_key not in db:
        LOG.error("invalid api key, no skills registered")
        return

    db[access_key].remove(skill_id)
    db.store()
    print(f"Skill removed from {access_key}: {skill_id}")


@multimind_cmds.command(help="lists skill for an access key", name="list-skills")
@click.argument("access_key", required=True, type=str)
def list_skill(access_key):
    db = JsonStorageXDG("multimind", subfolder="hivemind")
    if access_key not in db:
        LOG.error("invalid api key, no skills registered")
        return

    print("Allowed skills:", db[access_key])


if __name__ == "__main__":
    multimind_cmds()
