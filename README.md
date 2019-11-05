# Ocelot-collab
I am a user of Ocelot-Optimzier, I just added aps machine interface. Great thanks to people who made Ocelot-Optimizer!

The files I changed are:

generic_optim.py  (to add APSMachineInterface)

mint/opt_objects.py   (the wait() function)

mint/mint.py     (for checking the alarm in the error_func)

mint/normscales.py  (added APSMachineInterface,   however, I tried to use the full path of parameter file, it did not work, then I went back to parameters/anl_hyperparams.pkl -- then I had to run the Ocelot GUI at OcelotOptimizer-dev directory, which should not be, right? -- I will check this one later) --  it would be nice if can provide it through the GUI; currently, I used a link to change the parameter file)

GP/bayes_optimization.py  (changed the ucb parameters for ANL)

GP/OnlineGP.py   (added different kernel per Adi Hanuka's instruction -- it would be nice if we can choose it from the GUI)


added

mint/aps

parameters/aps

parameters/anl_hyperparams.pkl

