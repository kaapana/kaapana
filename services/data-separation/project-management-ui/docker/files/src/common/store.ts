import { ref, reactive } from 'vue'
import {UserItem} from '@/common/types';

const state = reactive({
  user: ref<UserItem | null>(null),
})

let resolveUser!: (user: UserItem) => void
const userLoaded = new Promise<UserItem>((resolve) => (resolveUser = resolve))

function updateUser(newUser: UserItem) {
  state.user = newUser
  resolveUser(newUser)
}

export default {
  state,
  userLoaded,
  updateUser,
}
