import collections
import random
from abc import ABC, abstractmethod


class FederatedAggregationStrategy(ABC):
    @abstractmethod
    def aggregate(self, site_model_weights_dict: dict, federated_round: int) -> dict:
        pass


class FedAvgAggregationStrategy(FederatedAggregationStrategy):
    def aggregate(self, site_model_weights_dict, federated_round):
        """
        FedAvg: Communication-efficient Learning of Deep networks from Decentralized Data (https://arxiv.org/abs/1602.05629)
        Sum model_weights up.
        Divide summed model_weights by num_sites.
        Return a site_model_weights_dict with always the same model_weights per site.

        Note:
        * perform averaging based on pointers on the dict keys obtained with .data_ptr()
        * solution from https://github.com/MIC-DKFZ/nnUNet/issues/2553
        * btw site_model_weights_dict looks like that: site_model_weights_dict = {"<siteA>": <model_weights_0> , "<siteB>": <model_weights_1>, ...}
        """

        # for sample-weighted aggregation, get number of samples per client and list of client_instance_names
        num_samples_per_client = dict()
        client_instance_names = []
        for site_idx, _ in enumerate(self.remote_instances):
            client_instance_names.append(
                self.remote_instances[site_idx]["instance_name"]
            )
            num_samples_per_client[self.remote_instances[site_idx]["instance_name"]] = (
                len(
                    self.remote_instances[site_idx]["allowed_datasets"][
                        self.remote_conf_data["data_form"]["dataset_name"]
                    ]["identifiers"]
                )
                if self.remote_conf_data["data_form"]["dataset_limit"] is None
                else self.remote_conf_data["data_form"]["dataset_limit"]
            )
        num_all_samples = sum(num_samples_per_client.values())
        print(
            f"Averaging model weights with client's dataset sizes: {num_samples_per_client} \
            and total number of samples of {num_all_samples}!"
        )

        # initialize network_weights with those of first client_instance
        list_of_network_parameters = list(site_model_weights_dict.values())
        network_weights = site_model_weights_dict[client_instance_names[0]]
        # get addresses of keys
        keys = list(network_weights.keys())
        address_key_dict = {}
        for k in keys:
            address = network_weights[k].data_ptr()
            if address not in address_key_dict.keys():
                address_key_dict[address] = [k]
            else:
                address_key_dict[address].append(k)

        # perform the fedavg
        for a in address_key_dict.keys():
            for client_instance_name, net in site_model_weights_dict.items():
                if client_instance_name == client_instance_names[0]:
                    # network weights of client_instance_names [0] are already in network_weights
                    pass
                else:
                    # weighted sum
                    network_weights[address_key_dict[a][0]] += (
                        net[address_key_dict[a][0]]
                        * num_samples_per_client[client_instance_name]
                    )
            # divided by num_all_samples
            network_weights[address_key_dict[a][0]] /= num_all_samples
            # modifying the 0th keys is sufficient as the other keys point to the same data

        # reformat to return
        return_model_weights_dict = collections.OrderedDict()
        for site in site_model_weights_dict.keys():
            return_model_weights_dict[site] = network_weights
        return return_model_weights_dict


class FederatedDaisyChainingAggregationStrategy(FederatedAggregationStrategy):
    def __init__(self, dc_rate: int, agg_rate: int):
        self.dc_rate = dc_rate
        self.agg_rate = agg_rate
        self.fed_avg = FederatedAggregationStrategy()

    def aggregate(self, site_model_weights_dict, federated_round):
        """
        FedDC: Federated Learning from Small Datasets (https://arxiv.org/abs/2110.03469)
        Daisy chaining if (federated_round % dc_rate) == (dc_rate - 1).
        Aggregate local models if (federated_round % agg_rate) == (agg_rate - 1).

        Input:
        * site_model_weights_dict: site_model_weights_dict = {"<siteA>": <model_weights_0> , "<siteB>": <model_weights_1>, ...}
        * federated_round: current federated communication round
        * agg_rate: aggregation rate; defines how often local model weights are aggregated (avereaged)
        * dc_rate: daisy chaining rate; defines how often local models are randomly sent to other site

        Output:
        * return_model_weights_dict: with eiter just randomly permuted site keys or aggregated model_weights.
        """

        # do either daisy-chaining or aggregation
        if (federated_round % self.dc_rate) == (self.dc_rate - 1):
            # daisy chaining
            site_keys = list(site_model_weights_dict.keys())
            shuffled_site_keys = random.sample(site_keys, len(site_keys))
            return_model_weights_dict = dict(
                zip(
                    shuffled_site_keys,
                    [site_model_weights_dict[key] for key in shuffled_site_keys],
                )
            )
        if (federated_round % self.agg_rate) == (self.agg_rate - 1):
            # aggregation via FedAvg
            return_model_weights_dict = self.fed_avg.aggregate(
                site_model_weights_dict, federated_round
            )
        if ((federated_round % self.agg_rate) != (self.agg_rate - 1)) and (
            (federated_round % self.dc_rate) != (self.dc_rate - 1)
        ):
            raise ValueError(
                "Error while FedDC: Neither Daisy Chaining nor Aggregation was computed!"
            )
        return return_model_weights_dict
