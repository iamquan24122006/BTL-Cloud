<?php
define('CLI_SCRIPT',true);
require '/var/www/moodle/config.php';
$m=json_decode(file_get_contents($CFG->dataroot.'/.distribution/fixture.json'),true,512,JSON_THROW_ON_ERROR);
$assert=function($condition){if(!$condition){throw new RuntimeException('Restored fixture mismatch');}};
foreach($m['courses'] as $short=>$id){$assert($DB->get_record('course',['id'=>$id],'*',MUST_EXIST)->shortname===$short);}
foreach($m['users'] as $u){$assert($DB->get_record('user',['id'=>$u['id']],'*',MUST_EXIST)->username===$u['username']);}
$fs=get_file_storage();
foreach($m['resources'] as $r){
    $matches=$fs->get_area_files($r['contextid'],'mod_resource','content',false,'id',false);
    $found=false;
    foreach($matches as $f){if($f->get_filename()===$r['name']&&hash('sha256',$f->get_content())===$r['sha256']){$found=true;}}
    $assert($found);
}
foreach($m['submissions'] as $s){
    $row=$DB->get_record('assign_submission',['id'=>$s['id']],'*',MUST_EXIST);
    $assert((int)$row->userid===(int)$s['userid']);
    $file=$fs->get_file($m['assignment']['contextid'],'assignsubmission_file','submission_files',$s['id'],'/',rawurldecode(basename($s['path'])));
    $assert($file&&hash('sha256',$file->get_content())===$s['sha256']);
    $grade=$DB->get_record('assign_grades',['assignment'=>$m['assignment']['id'],'userid'=>$s['userid']],'*',MUST_EXIST);
    $assert((float)$grade->grade===(float)$s['grade']);
}
echo json_encode(['status'=>'passed','source_ids_preserved'=>true,'courses'=>count($m['courses']),'users'=>count($m['users']),'resources'=>count($m['resources']),'submissions_and_grades'=>count($m['submissions'])],JSON_THROW_ON_ERROR)."\n";
