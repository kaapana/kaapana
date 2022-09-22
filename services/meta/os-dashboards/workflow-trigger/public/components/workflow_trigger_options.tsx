import React from 'react';

import { VisOptionsProps } from 'src/plugins/vis_default_editor/public';
import { WorkflowTriggerOptionProps } from '../types';

export const WorkflowTriggerOptions = (props: VisOptionsProps<WorkflowTriggerOptionProps>) => {
    return (
        <div className="form-group" id="plugin">
            <label>Font Size - {props.stateParams.fontSize}pt</label>
            <input type="range" onChange={e => props.setValue("fontSize", parseInt(e.target.value))} className="form-control" min={8} max={40} defaultValue={props.stateParams.fontSize} />
            <br/>
            <label>Margin - {props.stateParams.margin}px</label>
            <input type="range" onChange={e => props.setValue("margin", parseInt(e.target.value))} className="form-control" minLength={0} maxLength={30} defaultValue={props.stateParams.margin} />
            <br/><br/>
            <label>Button Title</label>
            <input type="text" onChange={e => props.setValue("buttonTitle", e.target.value)} defaultValue={props.stateParams.buttonTitle} className="form-control" />
            <br/>
        </div>
    );
}
