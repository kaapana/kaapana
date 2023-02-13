import request from '@/request'

export interface SecurityProvider {
  id: string;
  name: string;
  url: string;
  api_endpoints: string[];
}

const securityProviderService = {
  async getSecurityProviders() {
    const securityProviders: SecurityProvider[] = [];

    try {
      const response = await request.get('/security/api/provider');
      const { data } = response;
      const providerList = data.providers;
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
