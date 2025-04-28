We have to deactivate hardware sequencing on the engine level to make the queue implementation work. This is a limitation of the current implementation. 

```python
    from pymmcore_plus import CMMCorePlus
    
    mmc = CMMCorePlus()
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False
```