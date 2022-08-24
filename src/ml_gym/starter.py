from typing import List, Type, Dict, Any
from ml_gym.blueprints.blue_prints import BluePrint
from ml_gym.gym.gym import Gym
from ml_gym.persistency.logging import MLgymStatusLoggerCollectionConstructable
from ml_gym.modes import RunMode, ValidationMode
from ml_gym.validation.validator_factory import ValidatorFactory
from datetime import datetime
from ml_gym.util.logger import QueuedLogging
from multiprocessing import Queue
from ml_gym.io.config_parser import YAMLConfigLoader
from ml_gym.error_handling.exception import ValidationModeNotValidError
from pathlib import Path


class MLGymStarter:

    def __init__(self, blue_print_class: Type[BluePrint], validation_mode: ValidationMode, run_mode: RunMode, num_epochs: int,
                 gs_config_path: str, evaluation_config_path: str, text_logging_path: str, process_count: int,
                 gpus: List[int], log_std_to_file: bool,
                 logger_collection_constructable: MLgymStatusLoggerCollectionConstructable = None) -> None:
        self.blue_print_class = blue_print_class
        self.num_epochs = num_epochs
        self.validation_mode = validation_mode
        self.evaluation_config_path = evaluation_config_path
        self.text_logging_path = text_logging_path
        self.process_count = process_count
        self.log_std_to_file = log_std_to_file
        self.gpus = gpus
        self.gs_config_path = gs_config_path
        self.run_mode = run_mode
        if run_mode != RunMode.TRAIN:
            self.grid_search_id = Path(gs_config_path).parts[-2]
        else:
            self.grid_search_id = None
        self.logger_collection_constructable = logger_collection_constructable

    @staticmethod
    def _create_gym(process_count: int, device_ids, log_std_to_file: bool,
                    logger_collection_constructable: MLgymStatusLoggerCollectionConstructable) -> Gym:
        gym = Gym(process_count, device_ids=device_ids, log_std_to_file=log_std_to_file,
                  logger_collection_constructable=logger_collection_constructable)
        return gym

    @staticmethod
    def _setup_logging_environment(log_dir_path: str):
        if QueuedLogging._instance is None:
            queue = Queue()
            QueuedLogging.start_logging(queue, log_dir_path)

    @staticmethod
    def _stop_logging_environment():
        QueuedLogging.stop_listener()

    @staticmethod
    def _save_gs_config(gs_config_path: str, grid_search_id: str):
        # gs_logging_path = os.path.join(dashify_logging_path, grid_search_id)
        # os.makedirs(gs_logging_path, exist_ok=True)
        # copyfile(gs_config_path, os.path.join(gs_logging_path, os.path.basename(gs_config_path)))
        pass

    @staticmethod
    def _save_evaluation_config(evaluation_config_path: str, grid_search_id: str):
        # gs_logging_path = os.path.join(dashify_logging_path, grid_search_id)
        # os.makedirs(gs_logging_path, exist_ok=True)
        # copyfile(evaluation_config_path, os.path.join(gs_logging_path, os.path.basename(evaluation_config_path)))
        pass

    @staticmethod
    def _save_environment_config(environment_config_path: str, grid_search_id: str):
        pass

    def start(self):
        if self.grid_search_id is not None:
            grid_search_id = self.grid_search_id
        else:
            grid_search_id = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
            self._save_gs_config(self.gs_config_path, grid_search_id)

        self._setup_logging_environment(self.text_logging_path)
        gym = MLGymStarter._create_gym(process_count=self.process_count, device_ids=self.gpus, log_std_to_file=self.log_std_to_file,
                                       logger_collection_constructable=self.logger_collection_constructable)
        gs_config = YAMLConfigLoader.load(self.gs_config_path)
        if self.validation_mode == ValidationMode.NESTED_CV:
            self._save_evaluation_config(self.evaluation_config_path, grid_search_id)
            evaluation_config = YAMLConfigLoader.load(self.evaluation_config_path)
            self.run_nested_cv(gym=gym, gs_config=gs_config, cv_config=evaluation_config,
                               grid_search_id=grid_search_id, run_mode=self.run_mode)
        elif self.validation_mode == ValidationMode.CROSS_VALIDATION:
            self._save_evaluation_config(self.evaluation_config_path, grid_search_id)
            evaluation_config = YAMLConfigLoader.load(self.evaluation_config_path)
            self.run_cross_validation(gym=gym, gs_config=gs_config, cv_config=evaluation_config,
                                      grid_search_id=grid_search_id, run_mode=self.run_mode)
        elif self.validation_mode == ValidationMode.GRID_SEARCH:
            self.run_grid_search(gym=gym, gs_config=gs_config, grid_search_id=grid_search_id, run_mode=self.run_mode)
        else:
            raise ValidationModeNotValidError
        self._stop_logging_environment()

    def run_nested_cv(self, gym: Gym, cv_config: Dict[str, Any], gs_config: Dict[str, Any], grid_search_id: str, run_mode: RunMode):
        nested_cv = ValidatorFactory.get_nested_cv(gs_config=gs_config,
                                                   cv_config=cv_config,
                                                   grid_search_id=grid_search_id,
                                                   blue_print_type=self.blue_print_class,
                                                   run_mode=run_mode)

        blueprints = nested_cv.create_blueprints(blue_print_type=self.blue_print_class,
                                                 gs_config=gs_config,
                                                 num_epochs=self.num_epochs,
                                                 logger_collection_constructable=self.logger_collection_constructable)
        gym.add_blue_prints(blueprints)
        gym.run(parallel=True)

    def run_cross_validation(self, gym: Gym, cv_config: Dict[str, Any], gs_config: Dict[str, Any], grid_search_id: str,
                             run_mode: RunMode):
        cross_validator = ValidatorFactory.get_cross_validator(gs_config=gs_config,
                                                               cv_config=cv_config,
                                                               grid_search_id=grid_search_id,
                                                               blue_print_type=self.blue_print_class,
                                                               run_mode=run_mode)

        blueprints = cross_validator.create_blueprints(blue_print_type=self.blue_print_class,
                                                       gs_config=gs_config,
                                                       num_epochs=self.num_epochs,
                                                       logger_collection_constructable=self.logger_collection_constructable)
        gym.add_blue_prints(blueprints)
        gym.run(parallel=True)

    def run_grid_search(self, gym: Gym, gs_config: Dict[str, Any], grid_search_id: str, run_mode: RunMode):
        gs_validator = ValidatorFactory.get_gs_validator(grid_search_id=grid_search_id,
                                                         run_mode=run_mode)
        blueprints = gs_validator.create_blueprints(blue_print_type=self.blue_print_class,
                                                    gs_config=gs_config,
                                                    num_epochs=self.num_epochs,
                                                    logger_collection_constructable=self.logger_collection_constructable)
        gym.add_blue_prints(blueprints)
        gym.run(parallel=True)
