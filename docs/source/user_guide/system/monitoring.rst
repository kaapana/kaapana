.. _monitoring:

Prometheus, Loki, Grafana
^^^^^^^^^^^^^^^^^^^^^^^^^

To keep track of the current status of the Kaapana platform, we've implemented a monitoring stack comprising Prometheus and Grafana. 
Prometheus collects and stores various metrics in the form of time series data, which can then be visualized through Grafana.
Additionally, we utilize `Loki <https://grafana.com/oss/loki/>`_ to collect and aggregate logs of all :term:`containers<container>`, which can also be visualized in Grafana.
Access Grafana via the System menu, where you can visually inspect crucial metrics such as disk space, CPU and GPU memory usage, and network pressure.