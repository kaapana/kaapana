import axios from 'axios';


const httpClient = axios.create({
  headers: {
    // "Content-Type": "application/json",
  }
});

//
// // interceptor to catch errors
// const errorInterceptor = error => {
//   // check if it's a server error
//   if (!error.response) {
//     notify.warn('Network/Server error');
//     return Promise.reject(error);
//   }
//
//   // all the other error responses
//   switch (error.response.status) {
//     case 400:
//       console.error(error.response.status, error.message);
//       notify.warn('Nothing to display', 'Data Not Found');
//       break;
//
//     case 401: // authentication error, logout the user
//       notify.warn('Please login again', 'Session Expired');
//       localStorage.removeItem('token');
//       router.push('/auth');
//       break;
//
//     default:
//       console.error(error.response.status, error.message);
//       notify.error('Server Error');
//
//   }
//   return Promise.reject(error);
// }
//
// // Interceptor for responses
// const responseInterceptor = response => {
//   switch (response.status) {
//     case 200:
//       // yay!
//       break;
//     // any other cases
//     default:
//     // default case
//   }
//
//   return response;
// }
//
// httpClient.interceptors.response.use(responseInterceptor, errorInterceptor);

export default httpClient;
