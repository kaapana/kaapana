# Airflow parses only files that mention "airflow" and "dag" (safe mode); this comment keeps
# the deprecation banner in the UI. The former DAG body is in the git history.
raise DeprecationWarning("This DAG is deprecated since version >=0.5.0.")
