package com.kaapana.usersync.http;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ProjectDto {
    public String id;
    public String external_id;
    public String name;
    public Integer int_id;
    public String description;
    public String kubernetes_namespace;
    public String s3_bucket;
    public String opensearch_index;
}
