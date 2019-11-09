# Timeslide example with GW150914

- [GW150914 GraceDB entry](https://gracedb.ligo.org/events/G184098)
- [GW150914 Bilby analysis setup](https://git.ligo.org/lscsoft/bilby/blob/master/examples/gw_examples/data_examples/GW150914_advanced.py)

## Using timeslides 
To use timeslides, a `gps-time-file` and `timeslide-file` are required. For example, condsider `timeshift_GW150914.ini`.

Run `bilby_pipe timeshift_GW150914.ini` to start three sets of analysis on `GW150914` with different timeslide Δt values. Descriptions of the jobs are as follows. 


## Results summary
The following table summarises three jobs using timeshifts and the various log Bayes Factors (lnBF) and log [Bayesian Coherence Ratios](https://arxiv.org/abs/arXiv:1803.09783): 

|   	| GPS Time                      	| H1 Δt 	| L1 Δt 	| Timeshifted to                        	| lnBCR 	| LnBF 	| H1 LnBF 	| L1 LnBF 	|
|---	|-------------------------------	|-------	|-------	|---------------------------------------	|-------	|------	|--------	|--------	|
| 1 	| GW150914: 1126259460.4        	| 0     	| 0     	| -                                     	| 12.6  	| 299  	| 191    	| 90     	|
| 2 	| GW150914 -1000s: 1126258460.4 	| 1000  	| 1000  	| timshifted to GW150914                	| 22.5   	| 300  	| 193    	| 84     	|
| 3 	| GW150914 +500s: 1126259960.4  	| -500  	| 500   	| timeshift H1 to GW150914, L1 to noise 	| -4.6  	| 182  	| 199    	| -0.02    	|


From the table, we can see that 
- The results for (1) (2) match up and positively detect the signal
- For (3) there is a signal in H1 (high lnBF at H) and just noise in L1 (low lnBF at L), so the BCR is low.


