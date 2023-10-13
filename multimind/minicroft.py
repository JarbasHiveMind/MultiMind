from ovos_core.intent_services import IntentService
from ovos_core.skill_manager import SkillManager
from ovos_plugin_manager.skills import find_skill_plugins
from ovos_utils.log import init_service_logger, LOG
from ovos_utils.messagebus import FakeBus
from ovos_workshop.skills.fallback import FallbackSkill

init_service_logger("MultiMind")
LOG.set_level("DEBUG")


class MiniCroft(SkillManager):
    def __init__(self, skill_ids, *args, **kwargs):
        if "bus" in kwargs:
            bus = kwargs.pop("bus")
        else:
            bus = FakeBus()
        super().__init__(bus, *args, **kwargs)
        self.skill_ids = skill_ids
        self.intent_service = self._register_intent_services()

    def _register_intent_services(self):
        """Start up the all intent services and connect them as needed.

        Args:
            bus: messagebus client to register the services on
        """
        service = IntentService(self.bus)
        # Register handler to trigger fallback system
        self.bus.on(
            'mycroft.skills.fallback',
            FallbackSkill.make_intent_failure_handler(self.bus)
        )
        return service

    def load_plugin_skills(self):
        LOG.info("loading skill plugins")
        plugins = find_skill_plugins()
        for skill_id, plug in plugins.items():
            LOG.debug(skill_id)
            if skill_id not in self.skill_ids:
                continue
            if skill_id not in self.plugin_skills:
                self._load_plugin_skill(skill_id, plug)

    def run(self):
        """Load skills and update periodically from disk and internet."""
        self.status.set_alive()

        self.load_plugin_skills()

        self.status.set_ready()

        LOG.info("Skills all loaded!")


if __name__ == "__main__":
    from ovos_utils.process_utils import ProcessState
    from time import sleep

    # now get this under a hivemind-core and create an instance per hivemind user
    croft1 = MiniCroft(["skill-ovos-hello-world.openvoiceos"])
    croft1.start()
    while croft1.status.state != ProcessState.READY:
        sleep(1)
    print("croft 1 loaded")

    croft2 = MiniCroft(["skill-ovos-hello-world.openvoiceos"])
    croft2.start()
    while croft2.status.state != ProcessState.READY:
        sleep(1)
    print("croft 2 loaded")

    croft3 = MiniCroft(["skill-ovos-hello-world.openvoiceos"])
    croft3.start()
    while croft3.status.state != ProcessState.READY:
        sleep(1)
    print("croft 3 loaded")

    sleep(5)

    croft1.stop()
    croft2.stop()
    croft3.stop()

    sleep(1)

    assert croft1.status.state == ProcessState.STOPPING
    assert croft2.status.state == ProcessState.STOPPING
    assert croft3.status.state == ProcessState.STOPPING
