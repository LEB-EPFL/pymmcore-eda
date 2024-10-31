# mermaid flow chart for the project

```mermaid
graph TD;
    Engine
    Runner
    Queue
    Actuator

    Actuator -- MDAevent --> Queue
    Queue --> Runner
    Runner -- MDAEvent --> Engine
    Engine -- Image --> Runner
    Runner --> Image