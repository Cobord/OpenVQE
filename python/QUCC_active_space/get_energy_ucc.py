import scipy.optimize
from numpy import binary_repr

from qat.lang.AQASM import Program, X
from qat.qpus import get_default_qpu

from circuit import efficient_fermionic_ansatz


class EnergyUCC:
    def action_quccsd(self, theta_0, hamiltonian_sp, cluster_ops, hf_init_sp):
        qpu = 0
        prog = 0
        prog = Program()
        q = prog.qalloc(hamiltonian_sp.nbqbits)
        ket_hf = binary_repr(hf_init_sp)
        list_ket_hf = [int(c) for c in ket_hf]
        # print(list_ket_hf)
        for j in range(hamiltonian_sp.nbqbits):
            if int(list_ket_hf[j] == 1):
                prog.apply(X, q[j])
        list_exci = []
        for j in cluster_ops:
            s = j.terms[0].qbits
            list_exci.append(s)
        qpu = get_default_qpu()
        qprog = efficient_fermionic_ansatz(q, prog, list_exci, theta_0)
        circ = qprog.to_circ()
        job = circ.to_job(job_type="OBS", observable=hamiltonian_sp)
        res = qpu.submit(job)
        return res.value

    def prepare_hf_state(self, hf_init_sp, cluster_ops_sp):
        prog = Program()
        nbqbits = cluster_ops_sp[0].nbqbits
        ket_hf = binary_repr(hf_init_sp)
        list_ket_hf = [int(c) for c in ket_hf]
        qb = prog.qalloc(nbqbits)
        # print(list_ket_hf)
        for j in range(nbqbits):
            if int(list_ket_hf[j] == 1):
                prog.apply(X, qb[j])
        circuit = prog.to_circ()
        return circuit

    def count(self, gate, mylist):
        if type(gate) == type(str):
            gate = str(gate)
        if gate == gate.lower():
            gate = gate.upper()
        mylist = [str(i) for i in mylist]
        count = 0
        for i in mylist:
            if i.find("gate='{}'".format(gate)) == -1:
                pass
            else:
                count += 1
        return count

    def prepare_state_ansatz(self, hamiltonian_sp, hf_init_sp, cluster_ops, theta):
        prog = Program()
        q = prog.qalloc(hamiltonian_sp.nbqbits)
        ket_hf = binary_repr(hf_init_sp)
        list_ket_hf = [int(c) for c in ket_hf]
        # print(list_ket_hf)
        for j in range(hamiltonian_sp.nbqbits):
            if int(list_ket_hf[j] == 1):
                prog.apply(X, q[j])
        list_exci = []
        for j in cluster_ops:
            s = j.terms[0].qbits
            list_exci.append(s)
        qpu = get_default_qpu()
        qprog = efficient_fermionic_ansatz(q, prog, list_exci, theta)
        circ = qprog.to_circ()
        curr_state = circ
        return curr_state

    def get_energies(
        self,
        hamiltonian_sp,
        cluster_ops,
        cluster_ops_sp,
        hf_init_sp,
        theta_current1,
        theta_current2,
        FCI,
    ):
        iterations = {
            "minimum_energy_result1_guess": [],
            "minimum_energy_result2_guess": [],
            "theta_optimized_result1": [],
            "theta_optimized_result2": [],
        }
        result = {}
        tolerance = 10 ** (-5)
        method = "BFGS"
        print("tolerance= ", tolerance)
        print("method= ", method)
        theta_optimized_result1 = []
        theta_optimized_result2 = []
        opt_result1 = scipy.optimize.minimize(
            lambda theta: self.action_quccsd(
                theta, hamiltonian_sp, cluster_ops, hf_init_sp
            ),
            x0=theta_current1,
            method=method,
            tol=tolerance,
            options={"maxiter": 50000, "disp": True},
        )
        opt_result2 = scipy.optimize.minimize(
            lambda theta: self.action_quccsd(
                theta, hamiltonian_sp, cluster_ops, hf_init_sp
            ),
            x0=theta_current2,
            method=method,
            tol=tolerance,
            options={"maxiter": 50000, "disp": True},
        )

        xlist1 = opt_result1.x
        xlist2 = opt_result2.x

        for si in range(len(theta_current1)):
            theta_optimized_result1.append(xlist1[si])
        for si in range(len(theta_current2)):
            theta_optimized_result2.append(xlist2[si])
        curr_state_result1 = self.prepare_state_ansatz(
            hamiltonian_sp, hf_init_sp, cluster_ops, theta_optimized_result1
        )
        curr_state_result2 = self.prepare_state_ansatz(
            hamiltonian_sp, hf_init_sp, cluster_ops, theta_optimized_result2
        )
        gates1 = curr_state_result1.ops
        gates2 = curr_state_result2.ops
        CNOT1 = self.count("CNOT", gates1)
        CNOT2 = self.count("CNOT", gates2)
        iterations["minimum_energy_result1_guess"].append(opt_result1.fun)
        iterations["minimum_energy_result2_guess"].append(opt_result2.fun)
        iterations["theta_optimized_result1"].append(theta_optimized_result1)
        iterations["theta_optimized_result2"].append(theta_optimized_result2)
        result["CNOT1"] = CNOT1
        result["CNOT2"] = CNOT2
        result["len_op1"] = len(theta_optimized_result1)
        result["len_op2"] = len(theta_optimized_result2)
        result["energies1_substracted_from_FCI"] = abs(opt_result1.fun - FCI)
        result["energies2_substracted_from_FCI"] = abs(opt_result2.fun - FCI)
        return iterations, result
