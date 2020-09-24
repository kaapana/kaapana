#bin/bash

function organ_segmentation {
    log="segmentation.log"
    echo "Organ segmentation - STARTED..."
    mkdir -p $OUTPUTDIR
    BATCH=false

    dir=""
    loop_counter=0

        
    for file in $(find $INPUTDIR  -name '*.nrrd'); do
        filename=$(basename -- "$file");
        dirname=$(basename -- "$(dirname "${f}")");
        if [ "$dir" = "$dirname" ]; then
            echo "skipping...";
            continue;
        fi
        echo "Organ segmentation - File: ${f}"
        ((++loop_counter))
        dir=$dirname
        filename="${filename%.*}";
        echo $filename
        
        echo " MODE: ${MODE}"
        echo "INPUTDIR: ${INPUTDIR}"
        echo "OUTPUTDIR: ${OUTPUTDIR}"
        echo "filename: ${filename}"
        echo "file: ${file}"
        IFS=/ read -a path_array <<< $file
        len_array=${#path_array[@]}

        dag_run_dir="${path_array[$len_array-4]}"
        tmp_path=$dag_run_dir/tmp
        echo "DAGRUN DIR: " $dag_run_dir
        echo "TMP DIR: " $tmp_path

        case $MODE in
            unityCS)
                echo "File {$file}"
                echo "Output dir {$OUTPUTDIR}"
                echo "filename {$filename}"
                output_file="$OUTPUTDIR/${filename}-unityCS.nrrd"

                /opt/bin/ShapeModelMiniApps $file $output_file -i 1 CreateUnifiedGeometryImage
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS ERROR!";
                    exit 1;
                else
                    echo "unityCS OK"!
                fi
            ;;
            
            Liver)
                mkdir -p $OUTPUTDIR/tmp/
                output_file="$OUTPUTDIR/tmp/${filename}-Liver.stl"

                /opt/bin/ShapeModelMiniApps $file /opt/modeldir/Liver /opt/modeldir/Liver/parameters.dat $output_file CreateShapeModelSegmentation
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-Liver ERROR!";
                    exit 1;
                else
                    echo "unityCS-Liver.STL OK"!
                fi
                output_file="$OUTPUTDIR/tmp/${filename}-Liver.nrrd"

                /opt/bin/ShapeModelMiniApps $OUTPUTDIR/tmp/${filename}-Liver.stl $file $output_file ConvertMeshToImage
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-Liver.nrrd  ERROR!";
                    exit 1;
                else
                    echo "unityCS-Liver.nrrd  ALL OK"!
                fi
                output_file="$OUTPUTDIR/${filename}-seg-Liver.nrrd "

                /opt/bin/ShapeModelMiniApps $file $OUTPUTDIR/tmp/${filename}-Liver.nrrd $output_file -i 1 ConvertSegmentationGeometry
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "-Liver.nrrd ERROR!";
                    exit 1;
                else
                    echo "-Liver.nrrd OK"!
                    rm -rf $OUTPUTDIR/tmp/
                fi
            ;;
            Spleen)
                mkdir -p $OUTPUTDIR/tmp/
                output_file="$OUTPUTDIR/${filename}-Spleen.stl"

                /opt/bin/ShapeModelMiniApps $file /opt/modeldir/Spleen /opt/modeldir/Spleen/parameters.dat $output_file CreateShapeModelSegmentation
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-Spleen.stl ERROR!";
                    exit 1;
                else
                    echo "unityCS-Spleen.stl OK"!
                fi
                output_file="$OUTPUTDIR/tmp/${filename}-Spleen.nrrd"

                /opt/bin/ShapeModelMiniApps $OUTPUTDIR/${filename}-Spleen.stl $file $output_file ConvertMeshToImage
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-Spleen.nrrd ERROR!";
                    exit 1;
                else
                    echo "unityCS-Spleen.nrrd OK"!
                fi
                output_file="$OUTPUTDIR/${filename}-seg-Spleen.nrrd"

                /opt/bin/ShapeModelMiniApps $file $OUTPUTDIR/tmp/${filename}-Spleen.nrrd $output_file -i 1 ConvertSegmentationGeometry
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "-Spleen.nrrd  ERROR!";
                    exit 1;
                else
                    echo "-Spleen.nrrd  OK"!
                    rm -rf $OUTPUTDIR/tmp/
                fi
            ;;
            LeftKidney)
                mkdir -p $OUTPUTDIR/tmp/
                cp -r $SPLEENDIR/* $OUTPUTDIR/tmp/
                output_file="$OUTPUTDIR/tmp/${filename}-LeftKidney.stl"

                /opt/bin/ShapeModelMiniApps $file /opt/modeldir/LeftKidney /opt/modeldir/LeftKidney/parameters.dat $output_file CreateShapeModelSegmentation
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-LeftKidney.stl ERROR!";
                    exit 1;
                else
                    echo "unityCS-LeftKidney.stl OK"!
                fi
                output_file="$OUTPUTDIR/tmp/${filename}-LeftKidney.nrrd"

                /opt/bin/ShapeModelMiniApps $OUTPUTDIR/tmp/${filename}-LeftKidney.stl $file $output_file ConvertMeshToImage
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-LeftKidney.nrrd ERROR!";
                    exit 1;
                else
                    echo "unityCS-LeftKidney.nrrd OK"!
                fi
                output_file="$OUTPUTDIR/${filename}-seg-LeftKidney.nrrd"
	            /opt/bin/ShapeModelMiniApps $file $OUTPUTDIR/tmp/${filename}-LeftKidney.nrrd $output_file -i 1 ConvertSegmentationGeometry
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "-LeftKidney.nrrd ERROR!";
                    exit 1;
                else
                    echo "-LeftKidney.nrrd  OK"!
                    rm -rf $OUTPUTDIR/tmp/
                fi
            ;;
            RightKidney)
                mkdir -p $OUTPUTDIR/tmp/
                cp -r $SPLEENDIR/* $OUTPUTDIR/tmp/
                output_file="$OUTPUTDIR/tmp/${filename}-RightKidney.stl"
                
                /opt/bin/ShapeModelMiniApps $file /opt/modeldir/RightKidney /opt/modeldir/RightKidney/parameters.dat $output_file CreateShapeModelSegmentation
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-RightKidney.stl ERROR!";
                    exit 1;
                else
                    echo "unityCS-RightKidney.stl OK"!
                fi
                output_file="$OUTPUTDIR/tmp/${filename}-RightKidney.nrrd"

                /opt/bin/ShapeModelMiniApps $OUTPUTDIR/tmp/${filename}-RightKidney.stl $file $output_file ConvertMeshToImage
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "unityCS-RightKidney.nrrd  ERROR!";
                    exit 1;
                else
                    echo "unityCS-RightKidney.nrrd OK"!

                fi
                output_file="$OUTPUTDIR/${filename}-seg-RightKidney.nrrd"

                /opt/bin/ShapeModelMiniApps $file $OUTPUTDIR/tmp/${filename}-RightKidney.nrrd $output_file -i 1 ConvertSegmentationGeometry
                RESULT=$?
                echo "RETURN_CODE: $RESULT"
                if ! { [ $RESULT -eq 1 ] && [ -f $output_file ]; }; then
                    echo "-RightKidney.nrrd ERROR!";
                    exit 1;
                else
                    echo "-RightKidney.nrrd OK"!
                    rm -rf $OUTPUTDIR/tmp/
                fi
            ;;
        esac
        
        if ! $BATCH ;
        then
            echo "No BATCH-mode - breaking loop..."
            break ;
        fi
        
    done

    rm -rf $OUTPUTDIR/tmp/

    if [ "$loop_counter" -gt 0 ]
    then
        echo "Organ segmentation done!";
        exit 0;
    else
        echo "No inputfile found!";
        exit 1;
    fi
}

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*    # list directories in the form "/tmp/dirname/"
do
        INPUTDIR="$dir/$OPERATOR_IN_DIR"
        OUTPUTDIR="$dir/$OPERATOR_OUT_DIR"
        SPLEENDIR="$dir/$SPLEEN_OPERATOR_DIR"
        echo ${INPUTDIR}
        echo ${OUTPUTDIR}
        echo ${SPLEENDIR}
        organ_segmentation
done