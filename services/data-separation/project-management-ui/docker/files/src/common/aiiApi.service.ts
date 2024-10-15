import axios, { AxiosResponse, AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';

const ACCESS_INFORMATION_BACKEND = import.meta.env.VITE_APP_ACCESS_INFORMATION_BACKEND || '/aii/';

const client = axios.create({
    baseURL: ACCESS_INFORMATION_BACKEND,
});

const token = "";

function header_with_auth_token(header_dict: any) {
    if (token) {
        header_dict['Authorization'] = `Bearer ${token}`;
    }
    return header_dict
}


const aiiApiGet = async function (suburl: string) {
    try {
        const response: AxiosResponse = await client.get(
            suburl,
            {
                headers: header_with_auth_token({})
            }
        );
        if (response.status === 200) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        }
        
    } catch (error: unknown) {
        throw error;
    }
}

const aiiApiPost = async function (suburl: string, data: Object) {
    const config: AxiosRequestConfig = {
        headers: header_with_auth_token({
        'Accept': 'application/json',
        }) as RawAxiosRequestHeaders,
    };

    try {
        const response: AxiosResponse = await client.post(suburl, data, config);
        if (response.status === 200) {
            return response.data;
        } else {
            throw new Error(response.status + " Error, Error Message: " + response.statusText);
        } 
      } catch (error: unknown) {
        throw error;
      }
}

export {aiiApiGet, aiiApiPost};