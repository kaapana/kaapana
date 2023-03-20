import request from '@/request'

interface APIEndpoint {
  identifier: string;
  endpoint: string;
}

export interface SecurityProvider {
  id: string;
  name: string;
  url: string;
  api_endpoints: APIEndpoint[];
}

const securityProviderService = {
  async getSecurityProviders() {
    const securityProviders: SecurityProvider[] = [];

    try {
      const response = await request.get('/security/api/providers');
      const { data } = response;
      const providerList = data["data"];
      for (const provider of providerList) {
        securityProviders.push(provider);
      }

    } catch(error) {
      console.error(`Something went wrong while retrieving security providers: ${error}`);
    }

    return securityProviders
  }
}

export default securityProviderService
