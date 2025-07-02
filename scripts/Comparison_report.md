# Mallory and ModelFuzz comparison

Mallory, a Reinforcement learning guided testing tool aims to discover bugs in distributed protocol implementations. Built on top of Jepsen, Mallory introduces a Reinforcement Learning agent to inject faults while learning to explore new states. 

Modelfuzz, achieves the same goal by fuzzing the implementation. Crucially, Modelfuzz simulates the executions of the implementation on a TLA+ Model and uses the states covered as guidance to generate new executions on the implementation. 

Key to the difference between the two approaches is the difference in the notion of states. Mallory defines states as a unique event trace - A graph of event with causally linked events connected by an edge. In contrast, a unique state in Modelfuzz is a concrete state in the TLA+ model. To compare, we ran Mallory with the prescribed parameters and measured the coverage in the TLA+ model (more details will follow).

The results are the Mallory fails to observe any meaningful coverage on the TLA+ model. Please find the coverage graph attached. The x-axis described time run for the experiment and y-axis measures the number of unique states.

## Experimental setup

We run ModelFuzz as described in the paper for the same duration as Mallory and simulate the trace obtained from Mallory on the TLA+ model. Our evaluation is constrained to the common RedisRaft benchmark. 

To enable the comparison, we need to collect the trace from Mallory in the same format as ModelFuzz and feed it to the TLA+ simulator. We augment the instrumented Redisraft binary with additional logging events and parse the logs to obtain the trace. 

For the specific benchmark, we run Mallory with the default parameters contained in the artifact with the following command

```
cd /host/tests/mallory/redisraft && lein run test --workload append --nemesis all --follower-proxy --time-limit 600 --nodes-file ~/nodes --test-count 1
```

Note the `time-limit` parameter is set to 600 seconds as described in the artifact documentation. However, this is different from the experimental results described in the Mallory paper. 

### Simulation limits

To simulate the trace on the TLA+ Model, we impose bounds on parameters of the model. For example, the maximum term that can be explored is 10. The bounds enable us to enumerate all possible actions and pick the next action according to the trace. Without the bounds, TLA+ model checker (TLC) does not allow us to simulate the trace explicitly.

Key parameter to this comparison is the number of client requests (read/write operations issued by Mallory and ModelFuzz). Mallory tests rely on feeding a large number of client requests (~order of 1000s) for large runs, and ~40-50 for the prescribed run. While we are able to simulate the trace on the shorter runs, it is infeasible to set such large bounds on the model due to state explosion and limitations of the TLA+ model checker.

## Explanation for the difference

We analyze the traces manually to understand the difference in coverage and make the following observations. 

1. ModelFuzz is aimed at maximimizing coverage of the restricted state space on the shorter runs thereby exploring all different behaviors. In contrast, Mallory is aimed at exploring the state space on larger runs with significantly blown-up state space. 
2. For the RedisRaft benchmark, Mallory traces fail to explore different scenarios where we observe successive leader elections without nodes committing (on the shorter runs) and therefore do no cover large parts of the state space. 
3. Abstracting away the parameters that blow-up the state space (number of client requests) does not lead to an increase in coverage. We measure this by running Mallory for longer runs (20mins) and simulating the trace on the model while ignoring the ClientRequest parameter of the events.