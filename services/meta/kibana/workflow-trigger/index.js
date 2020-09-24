
export default function (kibana) {
  return new kibana.Plugin({
    require: ['elasticsearch'],
    name: 'workflow_trigger',
    uiExports: {
      visTypes: [
        'plugins/workflow_trigger/workflow_trigger'
      ]
    },

    config(Joi) {
      return Joi.object({
        enabled: Joi.boolean().default(true),
      }).default();
    },

  });
};
