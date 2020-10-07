
import optionsTemplate from './workflow_trigger_options.html';
import { VisController } from './workflow_trigger_controller';

// import { CATEGORY } from 'ui/vis/vis_category';
import { VisFactoryProvider } from 'ui/vis/vis_factory';
import { Schemas } from 'ui/vis/editors/default/schemas';
import { VisTypesRegistryProvider } from 'ui/registry/vis_types';
import { FilterBarQueryFilterProvider } from 'ui/filter_bar/query_filter';

function ButtonVisProvider(Private) {
  const VisFactory = Private(VisFactoryProvider);
  const queryFilter = Private(FilterBarQueryFilterProvider);

  return VisFactory.createBaseVisualization({
    name: 'workflow_trigger',
    title: 'Start Process Button',
    icon: 'logstashIf',
    description: 'An actionable button',
    // category: CATEGORY.OTHER,
    visualization: VisController,
    visConfig: {
      defaults: {
        fontSize: 30,
        margin: 10,
        buttonTitle: 'SEND {{value}} RESULTS',
        filterprovider: queryFilter,
      },
    },
    editorConfig: {
      optionsTemplate: optionsTemplate,
      schemas: new Schemas([
        {
          group: 'metrics',
          name: 'metric',
          title: 'Metric',
          min: 1,
          aggFilter: ['!derivative', '!geo_centroid'],
          defaults: [
            { type: 'count', schema: 'metric' }
          ]
        }, {
          group: 'buckets',
          name: 'segment',
          title: 'Bucket Split',
          min: 0,
          max: 1,
          aggFilter: ['!geohash_grid', '!filter']
        }
      ]),
    }
  });
}

// register the provider with the visTypes registry
VisTypesRegistryProvider.register(ButtonVisProvider);

// export the provider so that the visType can be required with Private()
//export default ButtonVisProvider;
