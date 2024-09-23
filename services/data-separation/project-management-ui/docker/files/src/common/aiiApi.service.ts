import axios, { AxiosResponse, AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';

const ACCESS_INFORMATION_BACKEND = import.meta.env.VITE_APP_ACCESS_INFORMATION_BACKEND || '/aii/';

const client = axios.create({
    baseURL: ACCESS_INFORMATION_BACKEND,
});

const aiiApiGet = async function (suburl: string) {
    try {
        const response: AxiosResponse = await client.get(suburl);
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
        headers: {
        'Accept': 'application/json',
        } as RawAxiosRequestHeaders,
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