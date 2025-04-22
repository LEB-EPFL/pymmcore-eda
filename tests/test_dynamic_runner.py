def test_mda():
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            "/opt/micro-manager",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 1, "loops": 20},
    )

    from pymmcore_eda._runner import DynamicRunner

    runner = DynamicRunner()
    runner.set_engine(mmc.mda.engine)

    runner.run(mda_sequence)


if __name__ == "__main__":
    test_mda()
