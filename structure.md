# mermaid flow chart for the project

```mermaid
graph TD;
      
    subgraph pymmcore-eda
        BaseActuator
        SmartActuator
        QueueManager
        TimeMachine
        Analyser
        Interpreter
    end
    subgraph pymmcore-plus
        Engine
        Runner
    end
    Queue


    BaseActuator --> QueueManager
    SmartActuator --> QueueManager
    QueueManager -- MDAevent --> Queue
    QueueManager -- MDAEvent -->TimeMachine
    TimeMachine -- EventTime --> QueueManager
    Queue --> Runner
    Runner -- MDAEvent --> Engine
    Engine -- Image --> Runner
    Runner --> Image
    Image --> Analyser
    Analyser --> Interpreter
    Interpreter --> SmartActuator
```


# Actuator Queue interaction
```mermaid
graph TB;
    BaseActuator
    SmartActuator
    EventRegister
    subgraph TimeMachine
        direction TB
        Event -- if_reset_event_timer --> t0
    end

    QueueManager -- Events --> TimeMachine
    
    TimeMachine -- reset_Timers --> EventRegister

    subgraph EventRegister
        0.0 -.- 2.0
        0.0 -.- 1.0
        1.0 -.- 2.0
        2.0 -.- 3.0
        3.0 -.- 4.0
        
        subgraph 0.0
            Timer
            Events

        end
        subgraph 1.0[1.0 add upon registration]
            Events1(Events)
            Timer1(Timer)
        end
        subgraph 2.0
            Timer2(Timer)
            Events2(Events)
        end
        subgraph 3.0
            Timer3(Timer)
            Events3(Events)
        end        
        subgraph 4.0
            Timer4(Timer)
            Events4(Events)
        end

    end

    QueueManager
    Queue

    BaseActuator -- MDAEvents --> QueueManager
    QueueManager -- MDAEvent<br>min_start_time_0.0 --> 0.0

    SmartActuator -- smartMDAEvent --> QueueManager

    QueueManager -- smartMDAEvent<br>min_start_time_-1 --> 1.0
    QueueManager -- smartMDAEvent<br>t_idx_-1 --> Events2
    QueueManager -- smartMDAEvent<br>min_start_time_3.0 --> Events3


    Timer4 -- triggers --- X( ):::empty
    style X fill:transparent,stroke-width:0; 
    classDef empty width:0px,height:0px;
    Events4 --- X
    X --> Queue

    QueueManager --- Queue

    subgraph pymmcore-plus
        Runner
    end
    Queue --- Runner

```


