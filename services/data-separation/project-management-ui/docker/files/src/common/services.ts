import axios, { AxiosResponse, AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';

const ACCESS_INFORMATION_BACKEND = import.meta.env.VITE_APP_ACCESS_INFORMATION_BACKEND || '/aii/';
const KUBE_HELM = import.meta.env.VITE_APP_KUBE_HELM || '/kube-helm-api/';
const KAAPANA_BACKEND = import.meta.env.VITE_APP_KAAPANA_BACKEND || '/kaapana-backend/';

const AccessInformationInterfaceClient = axios.create({ baseURL: ACCESS_INFORMATION_BACKEND });
const kubeHelmClient = axios.create({ baseURL: KUBE_HELM });
const kaapanaBackendClient = axios.create({ baseURL: KAAPANA_BACKEND });

// Project-scoped calls use the platform-wide /project/<short_id>/ prefix,
// applied via baseURL here. The scope is the project MANAGED on the detail
// page (not the shell's selection): set by setScopedProject(), cleared on
// leave; the overview stays unscoped.
let scopedProjectSlug: string | null = null;

function setScopedProject(project: { short_id?: string; id?: string } | null): void {
    scopedProjectSlug = project?.short_id ?? project?.id ?? null;
}

function prefixProjectScope(config: AxiosRequestConfig): any {
    const slug = scopedProjectSlug;
    if (slug && config.baseURL && config.baseURL.startsWith('/') && !config.baseURL.startsWith('/project/')) {
        config.baseURL = `/project/${slug}${config.baseURL}`;
    }
    return config;
}
kubeHelmClient.interceptors.request.use(prefixProjectScope);
kaapanaBackendClient.interceptors.request.use(prefixProjectScope);

const token = "";

function header_with_auth_token(header_dict: any) {
    if (token) {
        header_dict['Authorization'] = `Bearer ${token}`;
    }
    return header_dict
}

const kubeHelmGet = async function (suburl: string) {
    try {
        const response: AxiosResponse = await kubeHelmClient.get(
            suburl,
            {
                headers: header_with_auth_token({})
            }
        );
        if (response.status >= 200 && response.status < 300) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }

    } catch (error: unknown) {
        throw error;
    }
}

const kubeHelmPost = async function (suburl: string, data: Object) {
    const config: AxiosRequestConfig = {
        headers: header_with_auth_token({
            'Accept': 'application/json',
        }) as RawAxiosRequestHeaders,
    };

    try {
        const response: AxiosResponse = await kubeHelmClient.post(suburl, data, config);
        if (response.status >= 200 && response.status < 300) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }
    } catch (error: unknown) {
        throw error;
    }
}


const aiiApiGet = async function (suburl: string) {
    try {
        const response: AxiosResponse = await AccessInformationInterfaceClient.get(
            suburl,
            {
                headers: header_with_auth_token({})
            }
        );
        if (response.status >= 200 && response.status < 300) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }

    } catch (error: unknown) {
        throw error;
    }
}

const aiiApiPost = async function (suburl: string, data: Object | null = null) {
    const config: AxiosRequestConfig = {
        headers: header_with_auth_token({
            'Accept': 'application/json',
        }) as RawAxiosRequestHeaders,
    };

    try {
        const response: AxiosResponse = await AccessInformationInterfaceClient.post(suburl, data, config);
        if (response.status >= 200 && response.status < 300) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }
    } catch (error: unknown) {
        throw error;
    }
}

const aiiApiPut = async function (suburl: string, params: Object, data: Object = {}) {
    const config: AxiosRequestConfig = {
        headers: header_with_auth_token({}),
        params: params
    };

    try {
        const response: AxiosResponse = await AccessInformationInterfaceClient.put(
            suburl,
            data,
            config,
        );
        if (response.status >= 200 && response.status < 300) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }
    } catch (error: unknown) {
        throw error;
    }
}

const aiiApiDelete = async function (suburl: string, params: Object = {}, data: Object = {}) {
    const config: AxiosRequestConfig = {
        headers: header_with_auth_token({}),
        data: data,
        params: params
    };
    try {
        const response: AxiosResponse = await AccessInformationInterfaceClient.delete(
            suburl,
            config,
        );
        if (response.status === 200) {
            return response.data;
        } else if (response.status === 204) {
            return response;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }

    } catch (error: unknown) {
        throw error;
    }
}
// ── Kaapana Backend API ─────────────────────────────────────────────────────

/**
 * Get all available DAGs (workflows) from kaapana-backend
 * @param onlyDagNames - If true, return only dag names; otherwise return full metadata
 * @param includeAll - If true, return all DAGs without AII filtering
 */
const kaapanaBackendGetDags = async function (onlyDagNames: boolean = true, includeAll: boolean = false) {
    const config: AxiosRequestConfig = {
        headers: header_with_auth_token({
            'Accept': 'application/json',
        }) as RawAxiosRequestHeaders,
        params: {
            only_dag_names: onlyDagNames,
            include_all: includeAll,
        }
    };

    try {
        const response: AxiosResponse = await kaapanaBackendClient.get(
            'client/dags',
            config
        );
        if (response.status >= 200 && response.status < 300) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }
    } catch (error: unknown) {
        throw error;
    }
};

export {
    aiiApiGet,
    aiiApiPost,
    aiiApiPut,
    aiiApiDelete,
    kubeHelmGet,
    kubeHelmPost,
    kaapanaBackendGetDags,
    setScopedProject,
};