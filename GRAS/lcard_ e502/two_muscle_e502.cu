#include <cstdio>
#include <cmath>
#include <utility>
#include <vector>
#include <ctime>
#include <cmath>
#include <stdexcept>
#include <random>
#include <curand_kernel.h>
#include <chrono>
#include <string>
// for file writing
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <unistd.h>
// colors
#define COLOR_RED "\x1b[1;31m"
#define COLOR_GREEN "\x1b[1;32m"
#define COLOR_RESET "\x1b[0m"
// IDE definitions
#ifdef __JETBRAINS_IDE__
#define __host__
#define __global__
#endif

/**
 6 cm/s = 125 [ms] has 30 slices
15 cm/s = 50 [ms] has 15 slices
21 cm/s = 25 [ms] has 6 slices
**/

using namespace std;

unsigned int global_id = 0;          //
const float SIM_STEP = 0.25;         // [ms] simulation step
unsigned int SIM_TIME_IN_STEPS;      //

// stuff variables
const int LEG_STEPS = 1;             // [step] number of full cycle steps
const int syn_outdegree = 20;        // synapse number outgoing from one neuron
const int neurons_in_ip = 50;        // number of neurons in interneuronal pool
const int neurons_in_moto = 50;      // motoneurons number
const int neurons_in_group = 15;     // number of neurons in a group
const int neurons_in_aff_ip = 50;    // number of neurons in interneuronal pool
const int neurons_in_afferent = 50;  // number of neurons in afferent

// neuron parameters
const float V_rest = -72;   // [mV] resting membrane potential
const float V_thld = -55;   // [mV] spike threshold
const float k = 0.7;        // [pA/mV] constant ("1/R")
const float a = 0.02;       // [ms⁻¹] time scale of the recovery variable U_m. Higher a, the quicker recovery
const float b = 0.2;        // [pA/mV] sensitivity of U_m to the sub-threshold fluctuations of the V_m
const float c = -80;        // [mV] after-spike reset value of V_m
const float d = 6;          // [pA] after-spike reset value of U_m
const float V_peak = 35;    // [mV] spike cutoff value
const float E_ex = 0.0;     // [mV] Reversal potential for excitatory input
const float E_in = -80.0;   // [mV] Reversal potential for inhibitory input
const float tau_syn_exc = 0.2;       // [ms] Decay time of excitatory synaptic current (ms)
const float tau_syn_inh = 2.0;       // [ms] Decay time of inhibitory synaptic current (ms)

class Group {
public:
	Group() = default;
	string group_name;
	unsigned int id_start{};
	unsigned int id_end{};
	unsigned int group_size{};
};

// struct for human-readable initialization of connectomes
struct SynapseMetadata {
	unsigned int pre_id;         // [id] pre neuron
	unsigned int post_id;        // [id] post neuron
	unsigned int synapse_delay;  // [step] synaptic delay of the synapse (axonal delay is included to this delay)
	float synapse_weight;        // [nS] synaptic weight. Interpreted as changing conductivity of neuron membrane

	SynapseMetadata(int pre_id, int post_id, float synapse_delay, float synapse_weight){
		this->pre_id = pre_id;
		this->post_id = post_id;
		this->synapse_delay = lround(synapse_delay * (1 / SIM_STEP) + 0.5);
		this->synapse_weight = synapse_weight;
	}
};

// struct for human-readable initialization of connectomes
struct GroupMetadata {
	Group group;
	float* g_exc;                // [nS] array of excitatory conductivity
	float* g_inh;                // [nS] array of inhibition conductivity
	float* voltage_array;        // [mV] array of membrane potential
	vector<float> spike_vector;  // [ms] spike times

	explicit GroupMetadata(Group group){
		this->group = move(group);
		voltage_array = new float[SIM_TIME_IN_STEPS];
		g_exc = new float[SIM_TIME_IN_STEPS];
		g_inh = new float[SIM_TIME_IN_STEPS];
	}
};

vector<GroupMetadata> all_groups;
vector<SynapseMetadata> all_synapses;

// form structs of neurons global ID and groups name
Group form_group(const string& group_name, int nrns_in_group = neurons_in_group) {
	Group group = Group();
	group.group_name = group_name;     // name of a neurons group
	group.id_start = global_id;        // first ID in the group
	group.id_end = global_id + nrns_in_group - 1;  // the latest ID in the group
	group.group_size = nrns_in_group;  // size of the neurons group

	all_groups.emplace_back(group);

	global_id += nrns_in_group;
	printf("Formed %s IDs [%d ... %d] = %d\n",
	       group_name.c_str(), global_id - nrns_in_group, global_id - 1, nrns_in_group);

	return group;
}

__host__
int ms_to_step(float ms) { return (int)(ms / SIM_STEP); }

__host__
float step_to_ms(int step) { return step * SIM_STEP; }


__global__
void neurons_kernel(unsigned short *V_m,
	                bool *nrn_has_spike,
	                const unsigned short *nrn_ref_time,
	                unsigned short *nrn_ref_time_timer,
	                const bool C0_activated,
	                const bool C0_early_activated,
	                const bool EES_activated,
	                const bool CV1_activated,
	                const bool CV2_activated,
	                const bool CV3_activated,
	                const bool CV4_activated,
	                const bool CV5_activated,
	                const unsigned short neurons_number){
	/**
	 *
	 */
	// get ID of the thread
	unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;

	// ignore threads which ID is greater than neurons number
	if (tid < neurons_number) {
		curandState localState;
		curand_init(nrn_ref_time_timer[tid] * V_m[tid], tid, 0, &localState);
		// reset spike flag of the current neuron before calculations
		nrn_has_spike[tid] = false;

		// generating spikes for EES
		if (tid <= 15 && EES_activated) nrn_has_spike[tid] = true;

		// iIP_F
		if (C0_activated && C0_early_activated && 952 <= tid && tid <= 1001) {
			nrn_has_spike[952 + static_cast<int>(neurons_in_ip * curand_uniform(&localState))] = true;
		}
		// skin stimulations
		if (!C0_activated) {
			if (tid == 90 && CV1_activated && curand_uniform(&localState) >= 0.5) nrn_has_spike[tid] = true;
			if (tid == 91 && CV2_activated && curand_uniform(&localState) >= 0.5) nrn_has_spike[tid] = true;
			if (tid == 92 && CV3_activated && curand_uniform(&localState) >= 0.5) nrn_has_spike[tid] = true;
			if (tid == 93 && CV4_activated && curand_uniform(&localState) >= 0.5) nrn_has_spike[tid] = true;
			if (tid == 94 && CV5_activated && curand_uniform(&localState) >= 0.5) nrn_has_spike[tid] = true;
		}

		// (threshold && not in refractory period)
		if ((V_m[tid] >= 65000) && (nrn_ref_time_timer[tid] == 0)) {
			V_m[tid] = 0;
			nrn_has_spike[tid] = true;
			nrn_ref_time_timer[tid] = nrn_ref_time[tid];
		} else {
			// if neuron in the refractory state -- ignore synaptic inputs. Re-calculate membrane potential
			if (nrn_ref_time_timer[tid] > 0 && (V_m[tid] < 20800 || V_m[tid] > 20820)) {
				// if membrane potential > -72
				if (V_m[tid] > 20820)
					V_m[tid] -= 5;
				else
					V_m[tid] += 5;
			}

			// update the refractory period timer
			if (nrn_ref_time_timer[tid] > 0)
				nrn_ref_time_timer[tid]--;
		}
	}
}

__global__
void synapses_kernel(unsigned short *V_m,
	                 const bool *nrn_has_spike,     // array of bools -- is neuron has spike or not
	                 const int *syn_pre_nrn_id,   // array of pre neurons ID per synapse
	                 const int *syn_post_nrn_id,  // array of post neurons ID per synapse
	                 const int *syn_delay,        // array of synaptic delay per synapse
	                 int *syn_delay_timer,        // array as above but changable
	                 const float *syn_weight,     // array of synaptic weight per synapse
	                 const int syn_number){            // number of synapses
	/**
	 *
	 */
	// get ID of the thread
	unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;

	// ignore threads which ID is greater than neurons number
	if (tid < syn_number) {
		// add synaptic delay if neuron has spike
		if (syn_delay_timer[tid] == -1 && nrn_has_spike[syn_pre_nrn_id[tid]])
			syn_delay_timer[tid] = syn_delay[tid];
		// if synaptic delay is zero it means the time when synapse increase I by synaptic weight
		if (syn_delay_timer[tid] == 0) {
			// post neuron ID = syn_post_nrn_id[syn_id], thread-safe (!)
			if (V_m[syn_post_nrn_id[tid]] > syn_weight[tid] && V_m[syn_post_nrn_id[tid]] < 65000)
				atomicAdd(&V_m[syn_post_nrn_id[tid]], syn_weight[tid]);
			// make synapse timer a "free" for next spikes
			syn_delay_timer[tid] = -1;
		}
		// update synapse delay timer
		if (syn_delay_timer[tid] > 0)
			syn_delay_timer[tid]--;
	}
}

void connect_one_to_all(const Group& pre_neurons,
	                    const Group& post_neurons,
	                    float syn_delay,
	                    float weight) {
	/**
	 *
	 */
	// Seed with a real random value, if available
	random_device r;
	default_random_engine generator(r());
	normal_distribution<float> delay_distr(syn_delay, syn_delay / 5);
	normal_distribution<float> weight_distr(weight, weight / 10);

	for (unsigned int pre_id = pre_neurons.id_start; pre_id <= pre_neurons.id_end; pre_id++) {
		for (unsigned int post_id = post_neurons.id_start; post_id <= post_neurons.id_end; post_id++) {
			all_synapses.emplace_back(pre_id, post_id, delay_distr(generator), weight_distr(generator));
		}
	}

	printf("Connect %s to %s [one_to_all] (1:%d). Total: %d W=%.2f, D=%.1f\n", pre_neurons.group_name.c_str(),
		   post_neurons.group_name.c_str(), post_neurons.group_size, pre_neurons.group_size * post_neurons.group_size,
		   weight, syn_delay);
}

void connect_fixed_outdegree(const Group& pre_neurons,
	                         const Group& post_neurons,
	                         float syn_delay,
	                         float syn_weight,
	                         int outdegree=syn_outdegree,
	                         bool no_distr=false) {
	/**
	 *
	 */
	// connect neurons with uniform distribution and normal distributon for syn delay and syn_weight
	random_device r;
	default_random_engine generator(r());
	uniform_int_distribution<int> id_distr(post_neurons.id_start, post_neurons.id_end);
	normal_distribution<float> delay_distr_gen(syn_delay, syn_delay / 5);
	normal_distribution<float> weight_distr_gen(syn_weight, syn_weight / 10);

	for (unsigned int pre_id = pre_neurons.id_start; pre_id <= pre_neurons.id_end; pre_id++) {
		for (int i = 0; i < outdegree; i++) {
			int rand_post_id = id_distr(generator);
			float syn_delay_distr = delay_distr_gen(generator);
			if (syn_delay_distr <= 0.2) {
				syn_delay_distr = 0.2;
			}
			unsigned short syn_weight_distr = static_cast<short>(weight_distr_gen(generator));
			if (no_distr) {
				all_synapses.emplace_back(pre_id, rand_post_id, syn_delay, syn_weight);
			} else {
				all_synapses.emplace_back(pre_id, rand_post_id, syn_delay_distr, syn_weight_distr);
			}
		}
	}

	printf("Connect %s to %s [fixed_outdegree] (1:%d). Total: %d W=%.2f, D=%.1f\n",
		   pre_neurons.group_name.c_str(), post_neurons.group_name.c_str(),
		   outdegree, pre_neurons.group_size * outdegree, syn_weight, syn_delay);
}

void init_network() {
	/// groups of neurons
	Group EES = form_group("EES");
	Group E1 = form_group("E1");
	Group E2 = form_group("E2");
	Group E3 = form_group("E3");
	Group E4 = form_group("E4");
	Group E5 = form_group("E5");

	Group CV1 = form_group("CV1", 1);
	Group CV2 = form_group("CV2", 1);
	Group CV3 = form_group("CV3", 1);
	Group CV4 = form_group("CV4", 1);
	Group CV5 = form_group("CV5", 1);

	Group OM1_0 = form_group("OM1_0");
	Group OM1_1 = form_group("OM1_1");
	Group OM1_2_E = form_group("OM1_2_E");
	Group OM1_2_F = form_group("OM1_2_F");
	Group OM1_3 = form_group("OM1_3");

	Group OM2_0 = form_group("OM2_0");
	Group OM2_1 = form_group("OM2_1");
	Group OM2_2_E = form_group("OM2_2_E");
	Group OM2_2_F = form_group("OM2_2_F");
	Group OM2_3 = form_group("OM2_3");

	Group OM3_0 = form_group("OM3_0");
	Group OM3_1 = form_group("OM3_1");
	Group OM3_2_E = form_group("OM3_2_E");
	Group OM3_2_F = form_group("OM3_2_F");
	Group OM3_3 = form_group("OM3_3");

	Group OM4_0 = form_group("OM4_0");
	Group OM4_1 = form_group("OM4_1");
	Group OM4_2_E = form_group("OM4_2_E");
	Group OM4_2_F = form_group("OM4_2_F");
	Group OM4_3 = form_group("OM4_3");

	Group OM5_0 = form_group("OM5_0");
	Group OM5_1 = form_group("OM5_1");
	Group OM5_2_E = form_group("OM5_2_E");
	Group OM5_2_F = form_group("OM5_2_F");
	Group OM5_3 = form_group("OM5_3");

	Group MN_E = form_group("MN_E", neurons_in_moto);
	Group MN_F = form_group("MN_F", neurons_in_moto);

	Group Ia_E_aff = form_group("Ia_E_aff", neurons_in_afferent);
	Group Ia_F_aff = form_group("Ia_F_aff", neurons_in_afferent);

	Group R_E = form_group("R_E");
	Group R_F = form_group("R_F");

	Group Ia_E_pool = form_group("Ia_E_pool", neurons_in_aff_ip);
	Group Ia_F_pool = form_group("Ia_F_pool", neurons_in_aff_ip);

	Group eIP_E = form_group("eIP_E", neurons_in_ip);
	Group eIP_F = form_group("eIP_F", neurons_in_ip);

	Group iIP_E = form_group("iIP_E", neurons_in_ip);
	Group iIP_F = form_group("iIP_F", neurons_in_ip);

	/// connectomes
	connect_fixed_outdegree(EES, E1, 1, 500, syn_outdegree, true);
	connect_fixed_outdegree(E1, E2, 1, 200, syn_outdegree, true);
	connect_fixed_outdegree(E2, E3, 1, 200, syn_outdegree, true);
	connect_fixed_outdegree(E3, E4, 1, 200, syn_outdegree, true);
	connect_fixed_outdegree(E4, E5, 1, 200, syn_outdegree, true);

	connect_one_to_all(CV1, iIP_E, 0.5, 50);
	connect_one_to_all(CV2, iIP_E, 0.5, 50);
	connect_one_to_all(CV3, iIP_E, 0.5, 50);
	connect_one_to_all(CV4, iIP_E, 0.5, 50);
	connect_one_to_all(CV5, iIP_E, 0.5, 50);

	/// OM 1
	// input from EES group 1
	connect_fixed_outdegree(E1, OM1_0, 2, 15);
	// input from sensory
	connect_one_to_all(CV1, OM1_0, 0.5, 10);
	connect_one_to_all(CV2, OM1_0, 0.5, 10);
	// [inhibition]
	connect_one_to_all(CV3, OM1_3, 1, 80);
	connect_one_to_all(CV4, OM1_3, 1, 80);
	connect_one_to_all(CV5, OM1_3, 1, 80);
	// inner connectomes
	connect_fixed_outdegree(OM1_0, OM1_1, 1, 50);
	connect_fixed_outdegree(OM1_1, OM1_2_E, 1, 22);
	connect_fixed_outdegree(OM1_1, OM1_2_F, 1, 27);
	connect_fixed_outdegree(OM1_1, OM1_3, 1, 2);
	connect_fixed_outdegree(OM1_2_E, OM1_1, 2.5, 22);
	connect_fixed_outdegree(OM1_2_F, OM1_1, 2.5, 27);
	connect_fixed_outdegree(OM1_2_E, OM1_3, 1, 2);
	connect_fixed_outdegree(OM1_2_F, OM1_3, 1, 4);
	connect_fixed_outdegree(OM1_3, OM1_1, 1, -5 );
	connect_fixed_outdegree(OM1_3, OM1_2_E, 0.5, -50);
	connect_fixed_outdegree(OM1_3, OM1_2_F, 1, -3);
	// output to OM2
	connect_fixed_outdegree(OM1_2_F, OM2_2_F, 4, 30);
	// output to IP
	connect_fixed_outdegree(OM1_2_E, eIP_E, 1, 12, neurons_in_ip); //16
	connect_fixed_outdegree(OM1_2_F, eIP_F, 4, 5, neurons_in_ip);

	/// OM 2
	// input from EES group 2
	connect_fixed_outdegree(E2, OM2_0, 2, 7);
	// input from sensory [CV]
	connect_one_to_all(CV2, OM2_0, 0.5, 10);
	connect_one_to_all(CV3, OM2_0, 0.5, 10);
	// [inhibition]
	connect_one_to_all(CV4, OM2_3, 1, 80);
	connect_one_to_all(CV5, OM2_3, 1, 80);
	// inner connectomes
	connect_fixed_outdegree(OM2_0, OM2_1, 1, 50);
	connect_fixed_outdegree(OM2_1, OM2_2_E, 1, 24);
	connect_fixed_outdegree(OM2_1, OM2_2_F, 1, 35);
	connect_fixed_outdegree(OM2_1, OM2_3, 1, 3);
	connect_fixed_outdegree(OM2_2_E, OM2_1, 2.5, 24);
	connect_fixed_outdegree(OM2_2_F, OM2_1, 2.5, 35);
	connect_fixed_outdegree(OM2_2_E, OM2_3, 1, 3);
	connect_fixed_outdegree(OM2_2_F, OM2_3, 1, 3);
	connect_fixed_outdegree(OM2_3, OM2_1, 1, -5);
	connect_fixed_outdegree(OM2_3, OM2_2_E, 1, -70);
	connect_fixed_outdegree(OM2_3, OM2_2_F, 1, -5); //-70
	// output to OM3
	connect_fixed_outdegree(OM2_2_F, OM3_2_F, 4, 30);
	// output to IP
	connect_fixed_outdegree(OM2_2_E, eIP_E, 2, 8, neurons_in_ip); // 5
	connect_fixed_outdegree(OM2_2_F, eIP_F, 4, 5, neurons_in_ip);

	/// OM 3
	// input from EES group 3
	connect_fixed_outdegree(E3, OM3_0, 1, 7);
	// input from sensory [CV]
	connect_one_to_all(CV3, OM3_0, 0.5, 10);
	connect_one_to_all(CV4, OM3_0, 0.5, 10);
	// [inhibition]
	connect_one_to_all(CV5, OM3_3, 1, 80);
	// inner connectomes
	connect_fixed_outdegree(OM3_0, OM3_1, 1, 50);
	connect_fixed_outdegree(OM3_1, OM3_2_E, 1, 23);
	connect_fixed_outdegree(OM3_1, OM3_2_F, 1, 30);
	connect_fixed_outdegree(OM3_1, OM3_3, 1, 3);
	connect_fixed_outdegree(OM3_2_E, OM3_1, 2.5, 23);
	connect_fixed_outdegree(OM3_2_F, OM3_1, 2.5, 25);
	connect_fixed_outdegree(OM3_2_E, OM3_3, 1, 3);
	connect_fixed_outdegree(OM3_2_F, OM3_3, 1, 3);
	connect_fixed_outdegree(OM3_3, OM3_1, 1, -70);
	connect_fixed_outdegree(OM3_3, OM3_2_E, 1, -70);
	connect_fixed_outdegree(OM3_3, OM3_2_F, 1, -5);
	// output to OM3
	connect_fixed_outdegree(OM3_2_F, OM4_2_F, 4, 30);
	// output to IP
	connect_fixed_outdegree(OM3_2_E, eIP_E, 2, 8, neurons_in_ip); // 7 - 8
	connect_fixed_outdegree(OM3_2_F, eIP_F, 4, 5, neurons_in_ip);

	/// OM 4
	// input from EES group 4
	connect_fixed_outdegree(E4, OM4_0, 2, 7);
	// input from sensory [CV]
	connect_one_to_all(CV4, OM4_0, 0.5, 10);
	connect_one_to_all(CV5, OM4_0, 0.5, 10);
	// inner connectomes
	connect_fixed_outdegree(OM4_0, OM4_1, 3, 50);
	connect_fixed_outdegree(OM4_1, OM4_2_E, 1, 25);
	connect_fixed_outdegree(OM4_1, OM4_2_F, 1, 23);
	connect_fixed_outdegree(OM4_1, OM4_3, 1, 3);
	connect_fixed_outdegree(OM4_2_E, OM4_1, 2.5, 25);
	connect_fixed_outdegree(OM4_2_F, OM4_1, 2.5, 20);
	connect_fixed_outdegree(OM4_2_E, OM4_3, 1, 3);
	connect_fixed_outdegree(OM4_2_F, OM4_3, 1, 3);
	connect_fixed_outdegree(OM4_3, OM4_1, 1, -70);
	connect_fixed_outdegree(OM4_3, OM4_2_E, 1, -70);
	connect_fixed_outdegree(OM4_3, OM4_2_F, 1, -3);
	// output to OM4
	connect_fixed_outdegree(OM4_2_F, OM5_2_F, 4, 30);
	// output to IP
	connect_fixed_outdegree(OM4_2_E, eIP_E, 2, 7, neurons_in_ip);
	connect_fixed_outdegree(OM4_2_F, eIP_F, 4, 5, neurons_in_ip);

	/// OM 5
	// input from EES group 5
	connect_fixed_outdegree(E5, OM5_0, 1, 7);
	// input from sensory [CV]
	connect_one_to_all(CV5, OM5_0, 0.5, 10);
	// inner connectomes
	connect_fixed_outdegree(OM5_0, OM5_1, 1, 50);
	connect_fixed_outdegree(OM5_1, OM5_2_E, 1, 26);
	connect_fixed_outdegree(OM5_1, OM5_2_F, 1, 30);
	connect_fixed_outdegree(OM5_1, OM5_3, 1, 3);
	connect_fixed_outdegree(OM5_2_E, OM5_1, 2.5, 26);
	connect_fixed_outdegree(OM5_2_F, OM5_1, 2.5, 30);
	connect_fixed_outdegree(OM5_2_E, OM5_3, 1, 3);
	connect_fixed_outdegree(OM5_2_F, OM5_3, 1, 3);
	connect_fixed_outdegree(OM5_3, OM5_1, 1, -70);
	connect_fixed_outdegree(OM5_3, OM5_2_E, 1, -20);
	connect_fixed_outdegree(OM5_3, OM5_2_F, 1, -3);
	// output to IP
	connect_fixed_outdegree(OM5_2_E, eIP_E, 1, 10, neurons_in_ip); // 2.5
	connect_fixed_outdegree(OM5_2_F, eIP_F, 4, 5, neurons_in_ip);

	/// reflex arc
	connect_fixed_outdegree(iIP_E, eIP_F, 0.5, -10, neurons_in_ip);
	connect_fixed_outdegree(iIP_F, eIP_E, 0.5, -10, neurons_in_ip);

	connect_fixed_outdegree(iIP_E, OM1_2_F, 0.5, -1, neurons_in_ip);
	connect_fixed_outdegree(iIP_E, OM2_2_F, 0.5, -1, neurons_in_ip);
	connect_fixed_outdegree(iIP_E, OM3_2_F, 0.5, -1, neurons_in_ip);
	connect_fixed_outdegree(iIP_E, OM4_2_F, 0.5, -1, neurons_in_ip);

	connect_fixed_outdegree(EES, Ia_E_aff, 1, 500);
	connect_fixed_outdegree(EES, Ia_F_aff, 1, 500);

	connect_fixed_outdegree(eIP_E, MN_E, 0.5, 5, neurons_in_moto); // 2.2
	connect_fixed_outdegree(eIP_F, MN_F, 5, 8, neurons_in_moto);

	connect_fixed_outdegree(iIP_E, Ia_E_pool, 1, 10, neurons_in_ip);
	connect_fixed_outdegree(iIP_F, Ia_F_pool, 1, 10, neurons_in_ip);

	connect_fixed_outdegree(Ia_E_pool, MN_F, 1, -4, neurons_in_ip);
	connect_fixed_outdegree(Ia_E_pool, Ia_F_pool, 1, -1, neurons_in_ip);
	connect_fixed_outdegree(Ia_F_pool, MN_E, 1, -4, neurons_in_ip);
	connect_fixed_outdegree(Ia_F_pool, Ia_E_pool, 1, -1, neurons_in_ip);

	connect_fixed_outdegree(Ia_E_aff, MN_E, 2, 8, neurons_in_moto);
	connect_fixed_outdegree(Ia_F_aff, MN_F, 2, 6, neurons_in_moto);

	connect_fixed_outdegree(MN_E, R_E, 2, 1);
	connect_fixed_outdegree(MN_F, R_F, 2, 1);

	connect_fixed_outdegree(R_E, MN_E, 2, -5, neurons_in_moto);
	connect_fixed_outdegree(R_E, R_F, 2, -10);

	connect_fixed_outdegree(R_F, MN_F, 2, -5, neurons_in_moto);
	connect_fixed_outdegree(R_F, R_E, 2, -10);
}

void save(int test_index, GroupMetadata &metadata, const string& folder){
	/**
	 *
	 */
	ofstream file;
	string file_name = "/dat/" + to_string(test_index) + "_" + metadata.group.group_name + ".dat";

	file.open(folder + file_name);
	// save voltage
	for (unsigned int sim_iter = 0; sim_iter < SIM_TIME_IN_STEPS; sim_iter++)
		file << metadata.voltage_array[sim_iter] << " ";
	file << endl;

	// save g_exc
	for (unsigned int sim_iter = 0; sim_iter < SIM_TIME_IN_STEPS; sim_iter++)
		file << 0 << " ";
	file << endl;

	// save g_inh
	for (unsigned int sim_iter = 0; sim_iter < SIM_TIME_IN_STEPS; sim_iter++)
		file << 0 << " ";
	file << endl;

	// save spikes
	for (float const& value: metadata.spike_vector) {
		file << value << " ";
	}
	file.close();

	cout << "Saved to: " << folder + file_name << endl;
}

void save_result(int test_index, int save_all) {
	/**
	 *
	 */
	string current_path = getcwd(nullptr, 0);

	printf("[Test #%d] Save %s results to: %s \n", test_index, (save_all == 0)? "MOTO" : "ALL", current_path.c_str());

	for(GroupMetadata &metadata : all_groups) {
		if (save_all == 0) {
			if(metadata.group.group_name == "MN_E")
				save(test_index, metadata, current_path);
			if(metadata.group.group_name == "MN_F")
				save(test_index, metadata, current_path);
		} else {
			save(test_index, metadata, current_path);
		}
	}
}

// copy data from host to device
template <typename type>
void memcpyHtD(type* host, type* gpu, unsigned int size) {
	cudaMemcpy(gpu, host, sizeof(type) * size, cudaMemcpyHostToDevice);
}

// copy data from device to host
template <typename type>
void memcpyDtH(type* gpu, type* host, unsigned int size) {
	cudaMemcpy(host, gpu, sizeof(type) * size, cudaMemcpyDeviceToHost);
}

// get datasize of current variable type and its number
template <typename type>
unsigned int datasize(unsigned int size) {
	return sizeof(type) * size;
}

// fill array with current value
template <typename type>
void init_array(type *array, unsigned int size, type value) {
	for(unsigned int i = 0; i < size; i++)
		array[i] = value;
}
// fill array by normal distribution
template <typename type>
void rand_normal_init_array(type *array, unsigned int size, type mean, type stddev) {
	random_device r;
	default_random_engine generator(r());
	normal_distribution<float> distr(mean, stddev);

	for(unsigned int i = 0; i < size; i++)
		array[i] = (type)distr(generator);
}

float get_skin_stim_time(int cms) {
	if (cms == 21)
		return 25.0;
	if (cms == 15)
		return 50.0;
	return 125.0;
}

void copy_data_to(GroupMetadata &metadata,
	              const float* nrn_v_m,
	              const bool *nrn_has_spike,
	              unsigned int sim_iter) {
	/**
	 *
	 */
	float nrn_mean_volt = 0;

	for(unsigned int tid = metadata.group.id_start; tid <= metadata.group.id_end; tid++) {
		nrn_mean_volt += nrn_v_m[tid];
		if (nrn_has_spike[tid]) {
			metadata.spike_vector.push_back(step_to_ms(sim_iter) + 0.25);
		}
	}
	metadata.voltage_array[sim_iter] = nrn_mean_volt / metadata.group.group_size;
}

__host__
void simulate(int cms, int ees, int save_all, int itest) {
	/**
	 *
	 */
	random_device r;
	default_random_engine generator(r());
	uniform_real_distribution<float> d_interneurons(3, 8);
	normal_distribution<float> d_motoneurons(57, 6);

	chrono::time_point<chrono::system_clock> simulation_t_start, simulation_t_end;

	const float skin_stim_time = get_skin_stim_time(cms);
	const unsigned int T_simulation = 11 * skin_stim_time * LEG_STEPS;
	// calculate how much steps in simulation time [steps]
	SIM_TIME_IN_STEPS = (unsigned int)(T_simulation / SIM_STEP);

	// calculate spike frequency and C0/C1 activation time in steps
	auto ees_spike_each_step = (unsigned int)(1000 / ees / SIM_STEP);
	auto steps_activation_C0 = (unsigned int)(5 * skin_stim_time / SIM_STEP);
	auto steps_activation_C1 = (unsigned int)(6 * skin_stim_time / SIM_STEP);

	// init neuron groups and connectomes
	init_network();

	const unsigned int neurons_number = global_id;
	const unsigned int synapses_number = static_cast<int>(all_synapses.size());

	/// CPU variables
	// neuron variables
	float nrn_V_m[neurons_number];             // [mV] neuron membrane potential
	bool nrn_has_spike[neurons_number];      // neuron state - has spike or not
	int nrn_ref_time[neurons_number];        // [step] neuron refractory time
	int nrn_ref_time_timer[neurons_number];  // [step] neuron refractory time timer

	init_array<float>(nrn_V_m, neurons_number, 20800);
	init_array<bool>(nrn_has_spike, neurons_number, false);  // by default neurons haven't spikes at start
	rand_normal_init_array<int>(nrn_ref_time, neurons_number, (int)(3 / SIM_STEP), (int)(0.4 / SIM_STEP));  // neuron ref time, aprx interval is (1.8, 4.2)
	init_array<int>(nrn_ref_time_timer, neurons_number, 0);  // by default neurons have ref_t timers as 0

	// synapse variables
	auto *synapses_delay = (int *) malloc(datasize<int>(synapses_number));
	auto *synapses_delay_timer = (int *) malloc(datasize<int>(synapses_number));
	auto *synapses_weight = (float *) malloc(datasize<float>(synapses_number));
	auto *synapses_pre_nrn_id = (int *) malloc(datasize<int>(synapses_number));
	auto *synapses_post_nrn_id = (int *) malloc(datasize<int>(synapses_number));
	init_array<int>(synapses_delay_timer, synapses_number, -1);

	// fill arrays of synapses
	unsigned int syn_id = 0;
	for(SynapseMetadata metadata : all_synapses) {
		synapses_pre_nrn_id[syn_id] = metadata.pre_id;
		synapses_post_nrn_id[syn_id] = metadata.post_id;
		synapses_delay[syn_id] = metadata.synapse_delay;
		synapses_weight[syn_id] = metadata.synapse_weight;
		syn_id++;
	}
	all_synapses.clear();

	// neuron variables
	float* gpu_nrn_V_m;
	bool* gpu_nrn_has_spike;
	int* gpu_nrn_ref_time;
	int* gpu_nrn_ref_time_timer;

	// synapse variables
	int* gpu_syn_delay;
	float* gpu_syn_weight;
	int* gpu_syn_pre_nrn_id;
	int* gpu_syn_post_nrn_id;
	int* gpu_syn_delay_timer;

	// allocate memory in the GPU
	cudaMalloc(&gpu_nrn_V_m, datasize<float>(neurons_number));
	cudaMalloc(&gpu_nrn_has_spike, datasize<bool>(neurons_number));
	cudaMalloc(&gpu_nrn_ref_time, datasize<int>(neurons_number));
	cudaMalloc(&gpu_nrn_ref_time_timer, datasize<int>(neurons_number));

	cudaMalloc(&gpu_syn_pre_nrn_id, datasize<int>(synapses_number));
	cudaMalloc(&gpu_syn_post_nrn_id, datasize<int>(synapses_number));
	cudaMalloc(&gpu_syn_weight, datasize<float>(synapses_number));
	cudaMalloc(&gpu_syn_delay, datasize<int>(synapses_number));
	cudaMalloc(&gpu_syn_delay_timer, datasize<int>(synapses_number));

	// copy data from CPU to GPU
	memcpyHtD<float>(nrn_V_m, gpu_nrn_V_m, neurons_number);
	memcpyHtD<bool>(nrn_has_spike, gpu_nrn_has_spike, neurons_number);
	memcpyHtD<int>(nrn_ref_time, gpu_nrn_ref_time, neurons_number);
	memcpyHtD<int>(nrn_ref_time_timer, gpu_nrn_ref_time_timer, neurons_number);

	memcpyHtD<int>(synapses_pre_nrn_id, gpu_syn_pre_nrn_id, synapses_number);
	memcpyHtD<int>(synapses_post_nrn_id, gpu_syn_post_nrn_id, synapses_number);
	memcpyHtD<float>(synapses_weight, gpu_syn_weight, synapses_number);
	memcpyHtD<int>(synapses_delay, gpu_syn_delay, synapses_number);
	memcpyHtD<int>(synapses_delay_timer, gpu_syn_delay_timer, synapses_number);

	// preparations for simulation
	int threads_per_block = 32;
	unsigned int nrn_num_blocks = neurons_number / threads_per_block + 1;
	unsigned int syn_num_blocks = synapses_number / threads_per_block + 1;

	auto total_nrn_threads = threads_per_block * nrn_num_blocks;
	auto total_syn_threads = threads_per_block * syn_num_blocks;

	printf("* * * Start GPU * * *\n");
	printf("Neurons kernel: %d threads (%.3f%% threads idle) [%d blocks x %d threads per block] mapped on %d neurons \n",
	       total_nrn_threads, (double)(total_nrn_threads - neurons_number) / total_nrn_threads * 100,
	       nrn_num_blocks, threads_per_block, neurons_number);
	printf("Synapses kernel: %d threads (%.3f%% threads idle) [%d blocks x %d threads per block] mapped on %d synapses \n",
	       total_syn_threads, (double)(total_syn_threads - synapses_number) / total_syn_threads * 100,
	       syn_num_blocks, threads_per_block, synapses_number);

	// stuff variables for controlling C0/C1 activation
	int local_iter = 0;
	bool C0_activated = false; // start from extensor
	bool C0_early_activated = false;
	unsigned int shift_time_by_step = 0;
	bool EES_activated;
	bool CV1_activated;
	bool CV2_activated;
	bool CV3_activated;
	bool CV4_activated;
	bool CV5_activated;
	unsigned int shifted_iter_time;

	int begin_C_spiking[5] = {ms_to_step(0),
	                          ms_to_step(skin_stim_time),
	                          ms_to_step(2 * skin_stim_time),
	                          ms_to_step(3 * skin_stim_time),
	                          ms_to_step(5 * skin_stim_time)};
	int end_C_spiking[5] = {ms_to_step(skin_stim_time - 0.1),
	                        ms_to_step(2 * skin_stim_time - 0.1),
	                        ms_to_step(3 * skin_stim_time - 0.1),
	                        ms_to_step(5 * skin_stim_time - 0.1),
	                        ms_to_step(6 * skin_stim_time - 0.1)};

	simulation_t_start = chrono::system_clock::now();
	// the main simulation loop
	for (unsigned int sim_iter = 0; sim_iter < SIM_TIME_IN_STEPS; sim_iter++) {
		CV1_activated = false;
		CV2_activated = false;
		CV3_activated = false;
		CV4_activated = false;
		CV5_activated = false;
		EES_activated = (sim_iter % ees_spike_each_step == 0);
		// if flexor C0 activated, find the end of it and change to C1
		if (C0_activated) {
			if (local_iter != 0 && local_iter % steps_activation_C0 == 0) {
				C0_activated = false;
				local_iter = 0;
				shift_time_by_step += steps_activation_C0;
			}
			if (local_iter != 0 && (local_iter + 400) % steps_activation_C0 == 0) {
				C0_early_activated = false;
			}
		// if extensor C1 activated, find the end of it and change to C0
		} else {
			if (local_iter != 0 && local_iter % steps_activation_C1 == 0) {
				C0_activated = true;
				local_iter = 0;
				shift_time_by_step += steps_activation_C1;
			}
			if (local_iter != 0 && (local_iter + 400) % steps_activation_C1 == 0) {
				C0_early_activated = true;
			}
		}
		shifted_iter_time = sim_iter - shift_time_by_step;
		// check the CV activation
		if ((begin_C_spiking[0] <= shifted_iter_time) && (shifted_iter_time < end_C_spiking[0])) CV1_activated = true;
		if ((begin_C_spiking[1] <= shifted_iter_time) && (shifted_iter_time < end_C_spiking[1])) CV2_activated = true;
		if ((begin_C_spiking[2] <= shifted_iter_time) && (shifted_iter_time < end_C_spiking[2])) CV3_activated = true;
		if ((begin_C_spiking[3] <= shifted_iter_time) && (shifted_iter_time < end_C_spiking[3])) CV4_activated = true;
		if ((begin_C_spiking[4] <= shifted_iter_time) && (shifted_iter_time < end_C_spiking[4])) CV5_activated = true;

		// update local iter (warning: can be resetted at C0/C1 activation)
		local_iter++;
		// invoke GPU kernel for neurons
		neurons_kernel<<<nrn_num_blocks, threads_per_block>>>(gpu_nrn_V_m,
		                                                      gpu_nrn_has_spike,
		                                                      gpu_nrn_ref_time,
		                                                      gpu_nrn_ref_time_timer,
		                                                      C0_activated,
		                                                      C0_early_activated,
		                                                      EES_activated,
		                                                      CV1_activated,
		                                                      CV2_activated,
		                                                      CV3_activated,
		                                                      CV4_activated,
		                                                      CV5_activated,
		                                                      neurons_number);

		// copy data from GPU
		memcpyDtH<float>(gpu_nrn_V_m, nrn_V_m, neurons_number);
		memcpyDtH<bool>(gpu_nrn_has_spike, nrn_has_spike, neurons_number);

		// fill records arrays
		for(GroupMetadata &metadata : all_groups) {
			if (save_all == 0) {
				if (metadata.group.group_name == "MN_E")
					copy_data_to(metadata, nrn_V_m, nrn_has_spike, sim_iter);
				if (metadata.group.group_name == "MN_F")
					copy_data_to(metadata, nrn_V_m, nrn_has_spike, sim_iter);
			} else
				copy_data_to(metadata, nrn_V_m, nrn_has_spike, sim_iter);
		}

		// invoke GPU kernel for synapses
		synapses_kernel<<<syn_num_blocks, threads_per_block>>>(gpu_nrn_V_m,
		                                                       gpu_nrn_has_spike,
		                                                       gpu_syn_pre_nrn_id,
		                                                       gpu_syn_post_nrn_id,
		                                                       gpu_syn_delay,
		                                                       gpu_syn_delay_timer,
		                                                       gpu_syn_weight,
		                                                       synapses_number);
	} // end of the simulation iteration loop
	simulation_t_end = chrono::system_clock::now();

	cudaDeviceSynchronize();  // tell the CPU to halt further processing until the CUDA has finished doing its business
	cudaDeviceReset();        // remove all all device allocations (destroy a CUDA context)
	// save recorded data
	save_result(itest, save_all);

	auto sim_time_diff = chrono::duration_cast<chrono::milliseconds>(simulation_t_end - simulation_t_start).count();
	printf("Elapsed %li ms (measured) | T_sim = %d ms\n", sim_time_diff, T_simulation);
	printf("%s x%f\n", 1.0 * T_simulation / sim_time_diff > 1? COLOR_GREEN "faster" COLOR_RESET: COLOR_RED "slower" COLOR_RESET, (float)T_simulation / sim_time_diff);
}

// runner
int main(int argc, char* argv[]) {
	int cms = atoi(argv[1]);
	int ees = atoi(argv[2]);
	int inh = atoi(argv[3]);
	int ped = atoi(argv[4]);
	int ht5 = atoi(argv[5]);
	int save_all = atoi(argv[6]);
	int itest = atoi(argv[7]);

	simulate(cms, ees, inh, ped, ht5, save_all, itest);

	return 0;
}