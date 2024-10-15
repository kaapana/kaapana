// store.js
import { ref, reactive } from 'vue'
import {UserItem} from '@/common/types';

const state = reactive({
  user : ref<UserItem|null>(null), // Initialize as null or a valid default
  fetching: false,
});

function updateUser(newUser: UserItem) {
  // Ensure reactivity by updating properties of the existing object
  // Object.assign(state.user, newUser); // Update user properties reactively
  state.user = newUser;
}

export default {
  state,
  updateUser
};