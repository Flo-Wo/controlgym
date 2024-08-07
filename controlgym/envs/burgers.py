import numpy as np
from controlgym.envs import PDE


class BurgersEnv(PDE):
    """
    ### Description

    This environment models the Burgers' equation, described by:
        du/dt =  diffusivity_constant * d^2u/dx^2 - u * du/dx

    ### Action Space, Observation Space, Rewards, Episode Termination

    See parent class `PDE` defined in pde.py for details.

    ### Arguments

    ```
    controlgym.make('burgers')
    ```
    optional arguments:
    [n_steps]: the number of discrete-time steps. Default is 100.
    [domain_length]: domain length of PDE. Default is 1.0.
    [integration_time]: numerical integration time step. Default is 0.001.
    [sample_time]: each discrete-time step represents (ts) seconds. Default is 0.05.
    [process_noise_cov]: process noise covariance coefficient. Default is 0.0.
    [sensor_noise_cov]: sensor noise covariance coefficient. Default is 0.25.
    [random_init_state_cov]: random initial state covariance coefficient. Default is 0.0.
    [target_state]: target state. Default is np.zeros(n_state).
    [init_state]: initial state. Default is
        np.cosh(10 * (self.domain_coordinates - 1 * self.domain_length / 2)) ** (-1).
    [diffusivity_constant]: diffusivity constant. Default is 0.001.
    [n_state]: dimension of state vector. Default is 256.
    [n_observation]: dimension of observation vector. Default is 10.
    [n_action]: dimension of control vector. Default is 8.
    [control_sup_width]: control support width. Default is 0.1.
    [Q_weight]: weight of state tracking cost. Default is 1.0.
    [R_weight]: weight of control cost. Default is 1.0.
    [action_limit]: limit of action. Default is None.
    [observation_limit]: limit of observation. Default is None.
    [reward_limit]: limit of reward. Default is None.
    [seed]: random seed. Default is 0.
    """

    def __init__(
        self,
        n_steps: int = 100,
        domain_length: float = 1.0,
        integration_time: float = 0.001,
        sample_time: float = 0.05,
        process_noise_cov: float = 0.0,
        sensor_noise_cov: float = 0.25,
        random_init_state_cov: float = 0.0,
        target_state: np.ndarray[float] = None,
        init_state: np.ndarray[float] = None,
        diffusivity_constant: float = 0.001,
        n_state: int = 256,
        n_observation: int = 10,
        n_action: int = 8,
        control_sup_width: float = 0.1,
        Q_weight: float = 1.0,
        R_weight: float = 1.0,
        action_limit: float = None,
        observation_limit: float = None,
        reward_limit: float = None,
        seed: int = 0,
    ):
        PDE.__init__(
            self,
            id="burgers",
            n_steps=n_steps,
            domain_length=domain_length,
            integration_time=integration_time,
            sample_time=sample_time,
            process_noise_cov=process_noise_cov,
            sensor_noise_cov=sensor_noise_cov,
            random_init_state_cov=random_init_state_cov,
            target_state=target_state,
            n_state=n_state,
            n_observation=n_observation,
            n_action=n_action,
            control_sup_width=control_sup_width,
            Q_weight=Q_weight,
            R_weight=R_weight,
            action_limit=action_limit,
            observation_limit=observation_limit,
            reward_limit=reward_limit,
            seed=seed,
        )

        if init_state is not None:
            self.init_state = init_state
        else:
            self.init_state = np.cosh(
                10 * (self.domain_coordinates - 1 * self.domain_length / 2)
            ) ** (-1)
            # NOTE(random reset)
            self.init_state = 2 * np.random.rand(n_state) - 1
        self.state = self.init_state
        self.diffusivity_constant = diffusivity_constant

        # compute control sup, observation matrix
        self.control_sup = self._compute_control_sup()
        self.C = self._compute_C()

        # TODO(my addition): project the reward matrix and the target state in the lower
        # dimensional observable space
        self.C_target_state = self.C @ self.target_state

    def _compute_fourier_linear_op(self):
        """Private function to compute the linear operator of the PDE in Fourier space.

        Args:
            None.

        Returns:
            Linear operator of the PDE in Fourier space.
        """
        fourier_linear_op = -self.diffusivity_constant * self.domain_wavenumbers**2
        return fourier_linear_op

    def _compute_fourier_nonlinear_op(self):
        """Private function to compute the nonlinear operator of the PDE in Fourier space.

        Args:
            None.

        Returns:
            A function that computes the nonlinear operator of the PDE in Fourier space.
        """

        def fourier_nonlinear_op(state_fourier, action):
            # aa_state is the anti-aliased state; meaning the state evaluated in
            # physical space on a grid with 3/2 times more points
            aa_factor = 3 / 2
            aa_state = aa_factor * np.fft.irfft(
                state_fourier, n=int(self.n_state * aa_factor)
            )
            right_hand_side = (
                -0.5j
                * self.domain_wavenumbers
                * (1 / aa_factor)
                * np.fft.rfft(aa_state**2)[0 : int(self.n_state / 2) + 1]
            ) + (np.fft.rfft(self.control_sup, axis=0) @ action)
            return right_hand_side

        return fourier_nonlinear_op

    def get_params_asdict(self):
        """Save the extra environment parameters as a dictionary.

        Args:
            None.

        Returns:
            a dictionary containing the parameters of the pde environment + extra parameters.
        """
        pde_dict = super().get_params_asdict()
        extra_data = {"diffusivity_constant": self.diffusivity_constant}
        return {**pde_dict, **extra_data}
