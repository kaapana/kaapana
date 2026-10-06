import { ref, reactive } from 'vue'
import {UserItem} from '@/common/types';

const state = reactive({
  user : ref<UserItem|null>(null),
});

function updateUser(newUser: UserItem) {
  state.user = newUser;
}

export default {
  state,
  updateUser
};